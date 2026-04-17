"""Eval framework for cohere-agent-cookbook.

Re-exports the framework from recipes/10-eval-framework for use across recipes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_framework_path = Path(__file__).resolve().parents[1] / "recipes" / "10-eval-framework" / "framework.py"
_spec = importlib.util.spec_from_file_location("cookbook_framework", _framework_path)

if _spec is not None and _spec.loader is not None:
    _framework = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_framework)

    EvalExample = _framework.EvalExample
    EvalResult = _framework.EvalResult
    Rubric = _framework.Rubric
    STANDARD_RUBRIC = _framework.STANDARD_RUBRIC
    evaluate_one = _framework.evaluate_one
    run_eval_suite = _framework.run_eval_suite
    render_report = _framework.render_report
    load_gold_set = _framework.load_gold_set

    __all__ = [
        "EvalExample",
        "EvalResult",
        "Rubric",
        "STANDARD_RUBRIC",
        "evaluate_one",
        "run_eval_suite",
        "render_report",
        "load_gold_set",
    ]
