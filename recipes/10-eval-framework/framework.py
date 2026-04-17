"""Recipe 10 — Evaluation framework for Cohere prompts.

Reusable evaluation harness. Imported by other recipes to regression-test
their prompts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class EvalExample:
    id: str
    prompt: str
    expected_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    regex_pattern: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    example_id: str
    score: float
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass
class Rubric:
    name: str
    criteria: list[Callable[[str, EvalExample], tuple[float, str | None]]]
    pass_threshold: float = 0.7


def keyword_presence(response: str, ex: EvalExample) -> tuple[float, str | None]:
    """Score based on required keywords present."""
    if not ex.expected_keywords:
        return 1.0, None
    missing = [kw for kw in ex.expected_keywords if kw.lower() not in response.lower()]
    if missing:
        return 1.0 - (len(missing) / len(ex.expected_keywords)), f"missing keywords: {missing}"
    return 1.0, None


def forbidden_absence(response: str, ex: EvalExample) -> tuple[float, str | None]:
    """Score based on forbidden keywords absent."""
    if not ex.forbidden_keywords:
        return 1.0, None
    present = [kw for kw in ex.forbidden_keywords if kw.lower() in response.lower()]
    if present:
        return 0.0, f"forbidden keywords present: {present}"
    return 1.0, None


def regex_match(response: str, ex: EvalExample) -> tuple[float, str | None]:
    """Score based on regex pattern matching."""
    if not ex.regex_pattern:
        return 1.0, None
    if re.search(ex.regex_pattern, response):
        return 1.0, None
    return 0.0, f"regex not matched: {ex.regex_pattern}"


# Standard rubric
STANDARD_RUBRIC = Rubric(
    name="standard",
    criteria=[keyword_presence, forbidden_absence, regex_match],
    pass_threshold=0.7,
)


def load_gold_set(path: Path) -> list[EvalExample]:
    """Load gold set from JSONL."""
    examples = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        record = json.loads(line)
        examples.append(
            EvalExample(
                id=record.get("id"),
                prompt=record["prompt"],
                expected_keywords=record.get("expected_keywords", []),
                forbidden_keywords=record.get("forbidden_keywords", []),
                regex_pattern=record.get("regex_pattern"),
                metadata=record.get("metadata", {}),
            )
        )
    return examples


def evaluate_one(response: str, ex: EvalExample, rubric: Rubric = STANDARD_RUBRIC) -> EvalResult:
    """Evaluate a single response against an example."""
    scores = []
    failures = []
    for criterion in rubric.criteria:
        score, failure = criterion(response, ex)
        scores.append(score)
        if failure:
            failures.append(failure)

    aggregate = sum(scores) / len(scores)
    return EvalResult(
        example_id=ex.id,
        score=aggregate,
        passed=aggregate >= rubric.pass_threshold,
        failures=failures,
    )


def run_eval_suite(
    examples: list[EvalExample],
    generate_fn: Callable[[str], str],
    rubric: Rubric = STANDARD_RUBRIC,
) -> list[EvalResult]:
    """Run the full eval suite; return results."""
    results = []
    for ex in examples:
        try:
            response = generate_fn(ex.prompt)
        except Exception as e:
            results.append(
                EvalResult(
                    example_id=ex.id, score=0.0, passed=False, failures=[f"generate error: {e}"]
                )
            )
            continue
        results.append(evaluate_one(response, ex, rubric))
    return results


def render_report(results: list[EvalResult]) -> str:
    passed = sum(1 for r in results if r.passed)
    agg = sum(r.score for r in results) / max(1, len(results))

    out = []
    out.append(f"# Eval Report")
    out.append("")
    out.append(f"- **Total**: {len(results)}")
    out.append(f"- **Passed**: {passed} ({100 * passed / len(results):.1f}%)")
    out.append(f"- **Aggregate score**: {agg:.3f}")
    out.append("")
    out.append(f"## Results")
    out.append("")
    out.append("| ID | Status | Score | Failures |")
    out.append("|----|--------|-------|----------|")
    for r in results:
        status = "✓" if r.passed else "✗"
        failures = "; ".join(r.failures) if r.failures else "—"
        out.append(f"| {r.example_id} | {status} | {r.score:.2f} | {failures} |")
    return "\n".join(out)


if __name__ == "__main__":
    # Demo
    examples = [
        EvalExample(
            id="test1",
            prompt="What is 2+2?",
            expected_keywords=["4"],
            forbidden_keywords=["I don't know"],
        ),
        EvalExample(
            id="test2",
            prompt="Hello",
            expected_keywords=["hello", "hi"],
            regex_pattern=r"\b(hi|hello)\b",
        ),
    ]

    def mock_generate(prompt: str) -> str:
        if "2+2" in prompt:
            return "The answer is 4."
        return "Hi there!"

    results = run_eval_suite(examples, mock_generate)
    print(render_report(results))
