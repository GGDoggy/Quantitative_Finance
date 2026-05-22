#!/usr/bin/env python3
"""Fail if new non-shim dependencies on src.plots are introduced.

Migration policy:
- Stage A: src.plots remains shim-only (re-export from src.plotlib public API).
- Stage B: gradually migrate imports from src.plots to src.plotlib/app registry.
- Stage C: remove shim once only shim + deprecation tests reference src.plots.
"""

from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = ROOT / "tools" / "src_plots_import_allowlist.txt"
def _iter_py_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if not any(part.startswith(".") for part in path.parts)
    ]


def _is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if parts and parts[0] == "src" and len(parts) > 1 and parts[1] == "plots":
        return True
    if rel.as_posix().startswith("test/plots/test_src_plots_deprecation"):
        return True
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


def _allowlist() -> set[str]:
    entries = set()
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            entries.add(line)
    return entries


def main() -> int:
    current = _current_import_files()
    allowed = _allowlist()

    new_deps = sorted(current - allowed)
    if not new_deps:
        print("OK: no new src.plots imports outside allowlist")
        return 0

    print("ERROR: new src.plots dependency detected.")
    print("Migrate imports to src.plotlib or app registry module instead:")
    for file in new_deps:
        print(f" - {file}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
