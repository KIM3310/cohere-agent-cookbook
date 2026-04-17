"""Recipe 09 — Streaming with interleaved tool calls.

Problem: User-facing UI needs to show tokens as they stream,
even when the agent is making tool calls mid-stream.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_time",
            "description": "Get current time for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    }
]


def mock_get_time(city: str) -> str:
    import datetime

    return datetime.datetime.now().isoformat()


def stream_with_tools(user_message: str, model: str = "command-r-plus-08-2024") -> None:
    try:
        import cohere  # type: ignore
    except ImportError:
        raise RuntimeError("cohere package required") from None

    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("Set COHERE_API_KEY")

    client = cohere.ClientV2(api_key=api_key)
    messages = [{"role": "user", "content": user_message}]

    for step in range(5):
        print(f"\n[Step {step + 1}] Streaming...")

        # Stream the response
        stream = client.chat_stream(
            model=model,
            messages=messages,
            tools=TOOLS,
        )

        text_buffer = ""
        tool_calls: list[dict] = []

        for event in stream:
            event_type = getattr(event, "type", None)

            if event_type == "content-delta":
                delta_text = event.delta.message.content.text
                print(delta_text, end="", flush=True)
                text_buffer += delta_text

            elif event_type == "tool-call-start":
                print(f"\n[→ calling tool: {event.delta.message.tool_calls.function.name}]", end="", flush=True)

            elif event_type == "tool-call-delta":
                # Arguments arrive incrementally
                pass

            elif event_type == "tool-call-end":
                tc = event.delta.message.tool_calls
                tool_calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                )

            elif event_type == "message-end":
                print("\n[stream ended]")
                break

        # If no tool calls, we're done
        if not tool_calls:
            return

        # Execute tool calls
        messages.append({"role": "assistant", "content": text_buffer, "tool_calls": tool_calls})
        for tc in tool_calls:
            args = json.loads(tc["arguments"])
            if tc["name"] == "get_time":
                output = mock_get_time(**args)
            else:
                output = "unknown tool"
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps({"result": output}),
                }
            )
            print(f"\n[tool {tc['name']} returned: {output}]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", required=True)
    args = parser.parse_args()

    stream_with_tools(args.message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
