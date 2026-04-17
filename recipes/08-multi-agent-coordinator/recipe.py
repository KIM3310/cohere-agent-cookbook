"""Recipe 08 — Multi-agent coordinator pattern with Cohere.

Problem: Task requires multiple specialist agents — research, analysis,
synthesis — working together.

Pattern: Coordinator agent routes subtasks to specialists.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common.client import CookbookClient  # noqa: E402


RESEARCHER_PREAMBLE = (
    "You are a research specialist. Given a question, you gather relevant facts "
    "and context. Focus on accuracy and citing sources. Keep output under 300 words."
)

ANALYST_PREAMBLE = (
    "You are an analyst. Given research findings, you identify patterns, "
    "implications, and key insights. Keep output structured and under 200 words."
)

WRITER_PREAMBLE = (
    "You are a writer. Given research and analysis, you synthesize a clear, "
    "compelling final answer for the user. Match the user's level of technical depth."
)

COORDINATOR_PREAMBLE = (
    "You are a coordinator. Given a user question, you decide which specialists "
    "to invoke and in what order. Output plan as JSON:\n"
    "{\"plan\": [\"researcher\", \"analyst\", \"writer\"], \"reasoning\": \"...\"}\n"
    "For simple questions, you can skip specialists and answer directly."
)


def researcher(question: str, client: CookbookClient) -> str:
    result = client.send(
        message=question,
        preamble=RESEARCHER_PREAMBLE,
        temperature=0.2,
    )
    return result.text


def analyst(question: str, research: str, client: CookbookClient) -> str:
    prompt = f"Question: {question}\n\nResearch:\n{research}\n\nProvide analysis."
    result = client.send(
        message=prompt,
        preamble=ANALYST_PREAMBLE,
        temperature=0.3,
    )
    return result.text


def writer(question: str, research: str, analysis: str, client: CookbookClient) -> str:
    prompt = (
        f"Question: {question}\n\n"
        f"Research:\n{research}\n\n"
        f"Analysis:\n{analysis}\n\n"
        f"Synthesize a final answer for the user."
    )
    result = client.send(
        message=prompt,
        preamble=WRITER_PREAMBLE,
        temperature=0.5,
    )
    return result.text


def run(question: str) -> dict:
    client = CookbookClient()

    # Step 1: coordinator decides plan
    plan_result = client.send(
        message=f"User question: {question}\n\nPlan?",
        preamble=COORDINATOR_PREAMBLE,
        temperature=0.0,
    )

    print(f"Coordinator plan:\n{plan_result.text}\n")

    # Step 2: execute the plan (for demo, we use all 3 specialists)
    artifacts: dict[str, str] = {}

    print("→ Researcher ...")
    artifacts["research"] = researcher(question, client)
    print(f"Research: {artifacts['research']}\n")

    print("→ Analyst ...")
    artifacts["analysis"] = analyst(question, artifacts["research"], client)
    print(f"Analysis: {artifacts['analysis']}\n")

    print("→ Writer ...")
    artifacts["final_answer"] = writer(
        question, artifacts["research"], artifacts["analysis"], client
    )
    print(f"Final: {artifacts['final_answer']}\n")

    return artifacts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--question", required=True)
    args = parser.parse_args()

    artifacts = run(args.question)
    print("\n=== Final Answer ===")
    print(artifacts["final_answer"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
