"""Cohere client wrapper with retry, telemetry, cost tracking.

The single entry point used by every recipe in this cookbook. Mirrors the
design of claude-agent-cookbook's CookbookClient for cross-cookbook portability.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

log = logging.getLogger("cohere_cookbook.client")

# Pricing reference (April 2026; update via env vars for finance reconciliation)
PRICING_USD_PER_MTOK = {
    "command-r-plus-08-2024": {"input": 2.50, "output": 10.00},
    "command-r-08-2024": {"input": 0.15, "output": 0.60},
    "command-r7b-12-2024": {"input": 0.0375, "output": 0.15},
    "command": {"input": 1.00, "output": 2.00},  # legacy
}

DEFAULT_MODEL = "command-r-plus-08-2024"


@dataclass
class SendResult:
    """Normalized result from a cookbook client call."""

    text: str
    tool_calls: list[dict[str, Any]]
    citations: list[dict[str, Any]]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    request_id: str
    raw: Any  # the underlying Cohere response for escape-hatch access


class BudgetExceededError(RuntimeError):
    pass


class CookbookClient:
    """Thin wrapper over the Cohere client with retries + cost tracking.

    Usage:
        client = CookbookClient()
        result = client.send(
            message="Summarize the document",
            documents=[{"title": "doc1", "snippet": "..."}],
            model="command-r-plus-08-2024",
        )
        print(result.text)
        print(result.cost_usd)
    """

    def __init__(
        self,
        api_key: str | None = None,
        default_model: str = DEFAULT_MODEL,
        max_retries: int = 5,
        budget_usd: float | None = None,
    ) -> None:
        api_key = api_key or os.getenv("COHERE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Cohere API key required. Set COHERE_API_KEY env var or pass api_key."
            )

        try:
            import cohere  # type: ignore

            self._client = cohere.ClientV2(api_key=api_key)
        except ImportError as e:
            raise RuntimeError(
                "cohere package required. Install via: pip install cohere>=5.13"
            ) from e

        self.default_model = default_model
        self.max_retries = max_retries
        self.budget_usd = budget_usd
        self.session_cost = 0.0

    def send(
        self,
        *,
        message: str | None = None,
        messages: list[dict] | None = None,
        model: str | None = None,
        preamble: str | None = None,
        tools: list[dict] | None = None,
        documents: list[dict] | None = None,
        chat_history: list[dict] | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        request_id: str | None = None,
    ) -> SendResult:
        """Send a chat request to Cohere. Returns normalized SendResult."""

        model = model or self.default_model
        request_id = request_id or f"req_{uuid.uuid4().hex[:12]}"

        if message is None and messages is None:
            raise ValueError("either `message` or `messages` must be provided")

        # Build request payload
        if messages is None:
            final_messages = [{"role": "user", "content": message}]
        else:
            final_messages = messages

        if preamble:
            final_messages = [{"role": "system", "content": preamble}] + final_messages

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": final_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if tools is not None:
            kwargs["tools"] = tools
        if documents is not None:
            kwargs["documents"] = documents

        log.info(
            "cohere.send",
            extra={
                "request_id": request_id,
                "model": model,
                "tools_count": len(tools) if tools else 0,
                "documents_count": len(documents) if documents else 0,
            },
        )

        # Retry loop
        last_exc: Exception | None = None
        start = time.time()
        for attempt in range(self.max_retries):
            try:
                response = self._client.chat(**kwargs)
                latency_ms = int((time.time() - start) * 1000)
                return self._normalize_response(response, model, request_id, latency_ms)
            except Exception as e:
                last_exc = e
                if self._is_retryable(e):
                    backoff = 2**attempt
                    log.warning(
                        "cohere.retry",
                        extra={
                            "request_id": request_id,
                            "attempt": attempt + 1,
                            "backoff_s": backoff,
                            "error": str(e),
                        },
                    )
                    time.sleep(backoff)
                else:
                    raise

        raise RuntimeError("retries exhausted") from last_exc

    def _is_retryable(self, exc: Exception) -> bool:
        # Cohere raises subclasses of CohereAPIError
        cls_name = exc.__class__.__name__
        if "RateLimitError" in cls_name:
            return True
        if "ServerError" in cls_name:
            return True
        if "TimeoutError" in cls_name:
            return True
        return False

    def _normalize_response(
        self, response: Any, model: str, request_id: str, latency_ms: int
    ) -> SendResult:
        # Extract text
        text = ""
        tool_calls: list[dict] = []
        citations: list[dict] = []

        # Cohere v2 response structure
        if hasattr(response, "message"):
            msg = response.message
            if hasattr(msg, "content") and msg.content:
                # content is a list of content blocks
                for block in msg.content:
                    if hasattr(block, "text"):
                        text += block.text
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append(
                        {
                            "id": getattr(tc, "id", None),
                            "name": getattr(tc.function, "name", None)
                            if hasattr(tc, "function")
                            else None,
                            "arguments": getattr(tc.function, "arguments", None)
                            if hasattr(tc, "function")
                            else None,
                        }
                    )
            if hasattr(msg, "citations") and msg.citations:
                for c in msg.citations:
                    citations.append(
                        {
                            "start": getattr(c, "start", None),
                            "end": getattr(c, "end", None),
                            "text": getattr(c, "text", None),
                            "sources": [
                                {
                                    "type": getattr(s, "type", None),
                                    "id": getattr(s, "id", None),
                                }
                                for s in getattr(c, "sources", [])
                            ],
                        }
                    )

        # Token counts
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage"):
            usage = response.usage
            if hasattr(usage, "tokens"):
                input_tokens = getattr(usage.tokens, "input_tokens", 0)
                output_tokens = getattr(usage.tokens, "output_tokens", 0)

        # Cost
        cost_usd = cost_for_tokens(model, input_tokens, output_tokens)
        self.session_cost += cost_usd

        if self.budget_usd is not None and self.session_cost > self.budget_usd:
            raise BudgetExceededError(
                f"Session cost ${self.session_cost:.4f} exceeded budget ${self.budget_usd:.4f}"
            )

        log.info(
            "cohere.success",
            extra={
                "request_id": request_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            },
        )

        return SendResult(
            text=text,
            tool_calls=tool_calls,
            citations=citations,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            request_id=request_id,
            raw=response,
        )


def cost_for_tokens(model: str, input_tokens: int, output_tokens: int) -> float:
    pricing = PRICING_USD_PER_MTOK.get(model)
    if not pricing:
        log.warning("Unknown model pricing", extra={"model": model})
        return 0.0
    return (input_tokens / 1_000_000) * pricing["input"] + (
        output_tokens / 1_000_000
    ) * pricing["output"]
