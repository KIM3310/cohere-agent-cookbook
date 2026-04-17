"""Recipe 02 — Multi-step tool use with Cohere Command.

Problem: Agent needs to chain multiple tool calls to complete a task.
Example: Book a flight requires search → compare → hold.

Usage:
    python -m recipes.02-multi-step-tool-use.recipe --goal "Book a flight from Seoul to Tokyo tomorrow"
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
            "name": "search_flights",
            "description": "Search for flights between two cities",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "date": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["origin", "destination", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_flights",
            "description": "Compare flights on price, duration, and airline",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_ids": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["flight_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "hold_flight",
            "description": "Place a 24h hold on the selected flight",
            "parameters": {
                "type": "object",
                "properties": {
                    "flight_id": {"type": "string"},
                    "passenger_name": {"type": "string"},
                },
                "required": ["flight_id", "passenger_name"],
            },
        },
    },
]


def search_flights(origin: str, destination: str, date: str) -> list[dict]:
    """Mock: return 3 flights."""
    return [
        {"id": "FL001", "airline": "Korean Air", "departure": "09:00", "price": 320, "duration_min": 135},
        {"id": "FL002", "airline": "ANA", "departure": "13:30", "price": 280, "duration_min": 140},
        {"id": "FL003", "airline": "JAL", "departure": "18:00", "price": 340, "duration_min": 130},
    ]


def compare_flights(flight_ids: list[str]) -> dict:
    data = {
        "FL001": {"airline": "Korean Air", "price": 320, "duration_min": 135, "score": 7.8},
        "FL002": {"airline": "ANA", "price": 280, "duration_min": 140, "score": 8.2},
        "FL003": {"airline": "JAL", "price": 340, "duration_min": 130, "score": 8.0},
    }
    filtered = {fid: data[fid] for fid in flight_ids if fid in data}
    best = max(filtered.items(), key=lambda kv: kv[1]["score"])
    return {"comparison": filtered, "recommended": best[0]}


def hold_flight(flight_id: str, passenger_name: str) -> dict:
    return {
        "hold_id": "H-" + flight_id + "-001",
        "flight_id": flight_id,
        "passenger_name": passenger_name,
        "expires_in_hours": 24,
        "status": "confirmed",
    }


TOOL_IMPLEMENTATIONS = {
    "search_flights": search_flights,
    "compare_flights": compare_flights,
    "hold_flight": hold_flight,
}


def run(goal: str, model: str = "command-r-plus-08-2024", max_steps: int = 8) -> SendResult:
    client = CookbookClient(default_model=model)

    messages = [{"role": "user", "content": goal}]
    preamble = (
        "You are a travel assistant. Use tools to complete the user's booking: "
        "search_flights to find options, compare_flights to evaluate, hold_flight to reserve. "
        "After hold_flight returns, provide a summary."
    )

    for step in range(max_steps):
        result = client.send(
            messages=messages,
            preamble=preamble if step == 0 else None,
            tools=TOOL_DEFINITIONS,
        )

        if not result.tool_calls:
            return result

        # Execute tool calls
        messages.append(
            {
                "role": "assistant",
                "content": result.text or "",
                "tool_calls": result.tool_calls,
            }
        )

        for tc in result.tool_calls:
            fn = TOOL_IMPLEMENTATIONS.get(tc["name"])
            if fn is None:
                output = {"error": f"unknown tool: {tc['name']}"}
            else:
                try:
                    args = json.loads(tc["arguments"]) if isinstance(tc["arguments"], str) else tc["arguments"]
                    output = fn(**args)
                except Exception as e:
                    output = {"error": str(e)}

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(output),
                }
            )

    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", required=True)
    parser.add_argument("--model", default="command-r-plus-08-2024")
    args = parser.parse_args()

    result = run(args.goal, model=args.model)
    print(f"Final: {result.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
