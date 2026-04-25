from __future__ import annotations

import compileall
from pathlib import Path


def test_common_and_recipes_compile() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert compileall.compile_dir(str(repo_root / "common"), quiet=1)
    assert compileall.compile_dir(str(repo_root / "recipes"), quiet=1)
