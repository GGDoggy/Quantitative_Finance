from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Iterable


TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
SIMULATION_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT}).*simulation.*\.npz$"
)


def format_time_step(time_step: float | str | Decimal) -> str:
    """Return a stable decimal representation for filenames and labels."""
    try:
        decimal_value = Decimal(str(time_step))
    except InvalidOperation as error:
        raise ValueError(f"Invalid time step: {time_step!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"Time step must be a positive finite value: {time_step!r}")

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def _iter_files(path: Path, suffix: str) -> Iterable[Path]:
    if not path.exists():
        return []
    return sorted(entry for entry in path.iterdir() if entry.is_file() and entry.suffix == suffix)


def _simulation_time_step_tokens(
    time_step: float,
    time_step_token: str | None = None,
) -> tuple[str, ...]:
    tokens: list[str] = []
    for token in (time_step_token, format_time_step(time_step), str(time_step)):
        if token is not None and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def find_simulation_files(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    time_step_tokens = set(_simulation_time_step_tokens(time_step, time_step_token))

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        match = SIMULATION_RE.match(file_path.name)
        if not match:
            continue
        if (
            match.group("product_id") != product_id
            or match.group("timestamp") != timestamp
        ):
            continue

        matched_time_step = match.group("time_step")
        if matched_time_step in time_step_tokens or float(matched_time_step) == time_step:
            candidates.append(file_path)

    return tuple(sorted(candidates))
