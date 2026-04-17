"""Recipe 07 — Reliable structured output with Cohere Command.

Problem: Get Command to reliably produce JSON matching a schema.
Pattern: Pydantic model + retry on validation failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient  # noqa: E402


class ExtractedInvoice(BaseModel):
    """Expected structured output from invoice text."""

    invoice_number: str = Field(description="Invoice number or ID")
    vendor_name: str = Field(description="Name of the billing party")
    total_amount: float = Field(description="Total amount owed")
    currency: str = Field(description="Currency code (e.g., USD, KRW)", default="USD")
    due_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    line_items: list[dict] = Field(default_factory=list)


SAMPLE_INVOICE = """
INVOICE #INV-2026-04812

Billed from: Cloud Services Inc.
Billed to:   Acme Corp

Services provided — March 2026:
  - API Gateway hosting        $ 1,240.00
  - Database storage (500 GB)  $   480.00
  - Network egress              $   180.00
                               --------
  Subtotal                     $ 1,900.00
  Tax (8%)                     $   152.00
                               ========
  TOTAL DUE                    $ 2,052.00

Due: 2026-04-30
"""


def extract_invoice(
    text: str,
    max_retries: int = 3,
    model: str = "command-r-plus-08-2024",
) -> ExtractedInvoice:
    client = CookbookClient(default_model=model)

    schema = ExtractedInvoice.model_json_schema()
    prompt = (
        f"Extract structured invoice data from this text. Return ONLY valid JSON matching this schema:\n\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        f"Invoice text:\n{text}\n\n"
        f"Return only the JSON object, no surrounding prose or markdown fences."
    )

    last_error: Optional[str] = None
    for attempt in range(max_retries):
        try_prompt = prompt
        if last_error is not None:
            try_prompt += (
                f"\n\nPrevious attempt failed validation with: {last_error}\n"
                f"Please fix the JSON to match the schema exactly."
            )

        result = client.send(
            message=try_prompt,
            preamble="You are a precise data extractor. Always return valid JSON matching the schema.",
            temperature=0.0,
        )

        # Strip any surrounding markdown
        text_out = result.text.strip()
        if text_out.startswith("```"):
            lines = text_out.split("\n")
            text_out = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

        try:
            data = json.loads(text_out)
            return ExtractedInvoice(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = str(e)
            continue

    raise RuntimeError(f"Failed to extract after {max_retries} attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--invoice-text", default=None, help="Path to invoice text file; uses sample if omitted")
    args = parser.parse_args()

    text = SAMPLE_INVOICE
    if args.invoice_text:
        text = Path(args.invoice_text).read_text()

    invoice = extract_invoice(text)
    print(f"Extracted:\n{invoice.model_dump_json(indent=2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
