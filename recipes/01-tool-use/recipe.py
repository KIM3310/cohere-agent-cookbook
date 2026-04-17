"""Recipe 01 — Single-turn tool use with Cohere Command.

Problem: Given a natural-language query, invoke the appropriate tool and
return a formatted answer grounded in the tool's output.

Usage:
    python -m recipes.01-tool-use.recipe --query "What's the weather in Seoul?"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient, SendResult  # noqa: E402


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city. Returns temperature and conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g., 'Seoul' or 'Tokyo'",
                    },
                    "units": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature units (default celsius)",
                    },
                },
                "required": ["city"],
            },
        },
    }
]


def get_weather(city: str, units: str = "celsius") -> dict:
    """Mock weather tool. In production, call a real weather API."""
    # Deterministic mock data for demonstration
    mock_data = {
        "Seoul": {"temp_c": 18, "condition": "partly cloudy", "humidity": 62},
        "Tokyo": {"temp_c": 20, "condition": "clear", "humidity": 58},
        "New York": {"temp_c": 12, "condition": "light rain", "humidity": 75},
    }
    data = mock_data.get(city, {"temp_c": 15, "condition": "unknown", "humidity": 60})
    temp = data["temp_c"] if units == "celsius" else round(data["temp_c"] * 9 / 5 + 32)
    return {
        "city": city,
        "temperature": temp,
        "units": units,
        "condition": data["condition"],
        "humidity_pct": data["humidity"],
    }


def run(query: str, model: str = "command-r-plus-08-2024") -> SendResult:
    """Run single-turn tool use. Returns the final SendResult."""
    client = CookbookClient(default_model=model)

    # Step 1: Call with tools, see if Cohere asks for a tool call
    result = client.send(
        message=query,
        tools=TOOL_DEFINITIONS,
        preamble=(
            "You are a helpful assistant that uses tools when needed. "
            "Always call a tool when the user's question requires live data."
        ),
    )

    # Step 2: Execute the tool call(s), if any
    if result.tool_calls:
        tool_results = []
        for tc in result.tool_calls:
            if tc["name"] == "get_weather":
                args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                output = get_weather(**args)
                tool_results.append(
                    {
                        "call": tc,
                        "output": output,
                    }
                )

        # Step 3: Send tool results back to get final answer
        messages = [
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": result.text if result.text else "",
                "tool_calls": result.tool_calls,
            },
        ]
        for tr in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tr["call"]["id"],
                    "content": json.dumps(tr["output"]),
                }
            )

        final = client.send(messages=messages, tools=TOOL_DEFINITIONS)
        return final

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Recipe 01: Tool use with Cohere")
    parser.add_argument("--query", required=True, help="Natural-language query")
    parser.add_argument("--model", default="command-r-plus-08-2024")
    args = parser.parse_args()

    result = run(args.query, model=args.model)
    print(f"Answer: {result.text}")
    print(f"\nTokens: in={result.input_tokens}, out={result.output_tokens}")
    print(f"Cost:   ${result.cost_usd:.6f}")
    print(f"Latency: {result.latency_ms} ms")

    if result.citations:
        print("\nCitations:")
        for c in result.citations:
            print(f"  - {c}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
