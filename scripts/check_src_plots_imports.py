#!/usr/bin/env python3
"""Fail if any Python module still imports ``src.plots``."""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
def _iter_py_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if not any(part.startswith(".") for part in path.parts)
    ]


def _is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if parts and parts[0] == "scripts" and parts[-1] == "check_src_plots_imports.py":
        return True
    return False


def _contains_src_plots_import(source: str) -> bool:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src.plots" or alias.name.startswith("src.plots."):
                    return True
        elif isinstance(node, ast.ImportFrom):
            if node.module == "src.plots" or (node.module and node.module.startswith("src.plots.")):
                return True
            if node.module == "src" and any(alias.name == "plots" for alias in node.names):
                return True
    return False


def _current_import_files() -> set[str]:
    found: set[str] = set()
    for path in _iter_py_files():
        if _is_ignored(path):
            continue
        source = path.read_text(encoding="utf-8")
        if _contains_src_plots_import(source):
            found.add(path.relative_to(ROOT).as_posix())
    return found

def main() -> int:
    current = _current_import_files()
    if not current:
        print("OK: no src.plots imports remain")
        return 0

    print("ERROR: src.plots import detected.")
    print("Migrate imports to src.plotlib or app-layer adapters instead:")
    for file in sorted(current):
        print(f" - {file}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
