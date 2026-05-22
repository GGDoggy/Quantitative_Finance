#!/usr/bin/env python3
"""Enforce import boundaries between plotlib/preprocess/gui layers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ImportRule:
    source_prefix: str
    forbidden_prefix: str


RULES = (
    ImportRule("src.plotlib.renderers", "src.preprocess"),
    ImportRule("src.plotlib.renderers", "gui"),
    ImportRule("src.preprocess.catalog", "src.plots"),
)


def _iter_python_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*.py")
        if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
    ]


def _module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_modules(tree: ast.AST) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported.add(node.module)
    return imported


def _matches_prefix(module: str, prefix: str) -> bool:
    return module == prefix or module.startswith(f"{prefix}.")


def main() -> int:
    violations: list[str] = []

    for path in _iter_python_files():
        module = _module_name(path)
        text = path.read_text(encoding="utf-8")
        imported = _imported_modules(ast.parse(text))

        for rule in RULES:
            if not _matches_prefix(module, rule.source_prefix):
                continue
            for imported_module in sorted(imported):
                if _matches_prefix(imported_module, rule.forbidden_prefix):
                    violations.append(
                        f"{module} imports forbidden dependency {imported_module} ({path.relative_to(ROOT)})"
                    )

    if violations:
        print("ERROR: import boundary violations detected:")
        for entry in violations:
            print(f" - {entry}")
        return 1

    print("OK: import boundaries respected")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
