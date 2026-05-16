from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Iterable

from src.simulation.constants import DEFAULT_RESOLVED_TIME


TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
SIMULATION_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})"
    rf"(?:-resolved-(?P<resolved_time>{TIME_STEP_RE_FRAGMENT}))?"
    r"-simulation-(?P<algorithm>.+)\.npz$"
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


def _simulation_value_tokens(
    value: float | None,
    value_token: str | None = None,
) -> tuple[str, ...]:
    if value is None:
        return ()

    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"Invalid resolved time: {value!r}") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise ValueError(f"Resolved time must be a non-negative finite value: {value!r}")

    normalized_value = decimal_value.normalize()
    if normalized_value == normalized_value.to_integral():
        formatted_value = format(normalized_value, "f")
    else:
        formatted_value = format(normalized_value, "f").rstrip("0").rstrip(".")

    tokens: list[str] = []
    for token in (value_token, formatted_value, str(value)):
        if token is not None and token not in tokens:
            tokens.append(token)
    return tuple(tokens)


def _matches_resolved_time(
    metadata_resolved_time: float | None,
    metadata_resolved_time_token: str | None,
    resolved_time: float | None,
    resolved_time_tokens: set[str],
) -> bool:
    if resolved_time is None:
        return True

    if metadata_resolved_time is None:
        return resolved_time == DEFAULT_RESOLVED_TIME

    return (
        metadata_resolved_time_token in resolved_time_tokens
        or metadata_resolved_time == resolved_time
    )


def parse_simulation_filename(filename: str) -> dict[str, object] | None:
    match = SIMULATION_RE.match(filename)
    if not match:
        return None

    resolved_time_token = match.group("resolved_time")
    return {
        "product_id": match.group("product_id"),
        "timestamp": match.group("timestamp"),
        "time_step": float(match.group("time_step")),
        "time_step_token": match.group("time_step"),
        "resolved_time": float(resolved_time_token) if resolved_time_token is not None else None,
        "resolved_time_token": resolved_time_token,
        "algorithm_name": match.group("algorithm"),
    }


def find_simulation_files(
    preprocessed_dir: Path,
    product_id: str,
    timestamp: str,
    time_step: float,
    time_step_token: str | None = None,
    resolved_time: float | None = None,
    resolved_time_token: str | None = None,
    algorithm_name: str | None = None,
) -> tuple[Path, ...]:
    candidates: list[Path] = []
    time_step_tokens = set(_simulation_time_step_tokens(time_step, time_step_token))
    resolved_time_tokens = set(_simulation_value_tokens(resolved_time, resolved_time_token))

    for file_path in _iter_files(preprocessed_dir, ".npz"):
        metadata = parse_simulation_filename(file_path.name)
        if metadata is None:
            continue
        if (
            metadata["product_id"] != product_id
            or metadata["timestamp"] != timestamp
        ):
            continue

        if not (
            metadata["time_step_token"] in time_step_tokens
            or metadata["time_step"] == time_step
        ):
            continue

        if algorithm_name is not None and metadata["algorithm_name"] != algorithm_name:
            continue

        if not _matches_resolved_time(
            metadata["resolved_time"],
            metadata["resolved_time_token"],
            resolved_time,
            resolved_time_tokens,
        ):
            continue

        candidates.append(file_path)

    return tuple(sorted(candidates))
