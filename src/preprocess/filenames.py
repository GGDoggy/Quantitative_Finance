"""Filename parsing and token helpers for preprocess datasets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Match

from src.preprocess.exceptions import PreprocessValidationError
from src.simulation.constants import DEFAULT_RESOLVED_TIME


DEFAULT_RESOLVED_TIME_FALLBACK = DEFAULT_RESOLVED_TIME

TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"

_RAW_LEVEL2_INIT_RE = re.compile(
    r"^level2-(?P<product_id>.+)-init-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_LEVEL2_UPDATES_RE = re.compile(
    r"^level2-(?P<product_id>.+)-updates-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_RAW_TRADE_RE = re.compile(
    r"^trade-(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})\.csv$"
)
_PREPROCESSED_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})-orderbook_for_plot\.npz$"
)
_SIMULATION_RE = re.compile(
    r"^(?P<product_id>.+)-(?P<timestamp>\d{8}\.\d{6})-"
    rf"(?P<time_step>{TIME_STEP_RE_FRAGMENT})"
    rf"(?:-resolved-(?P<resolved_time>{TIME_STEP_RE_FRAGMENT}))?"
    r"-simulation-(?P<algorithm>.+)\.npz$"
)


@dataclass(frozen=True)
class SimulationFileMetadata:
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str
    resolved_time: float | None
    resolved_time_token: str | None
    algorithm_name: str


def format_time_step(time_step: float | str | Decimal) -> str:
    """Return a stable decimal representation for filenames and labels."""
    try:
        decimal_value = Decimal(str(time_step))
    except InvalidOperation as error:
        raise PreprocessValidationError(f"Invalid time step: {time_step!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise PreprocessValidationError(
            f"Time step must be a positive finite value: {time_step!r}"
        )

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d.%H%M%S")


def match_raw_level2_init_filename(filename: str) -> Match[str] | None:
    return _RAW_LEVEL2_INIT_RE.match(filename)


def match_raw_level2_updates_filename(filename: str) -> Match[str] | None:
    return _RAW_LEVEL2_UPDATES_RE.match(filename)


def match_raw_trade_filename(filename: str) -> Match[str] | None:
    return _RAW_TRADE_RE.match(filename)


def match_preprocessed_filename(filename: str) -> Match[str] | None:
    return _PREPROCESSED_RE.match(filename)


def match_simulation_filename(filename: str) -> Match[str] | None:
    return _SIMULATION_RE.match(filename)


def is_preprocessed_filename(filename: str) -> bool:
    return match_preprocessed_filename(filename) is not None


def is_simulation_filename(filename: str) -> bool:
    return match_simulation_filename(filename) is not None


def parse_simulation_filename(filename: str) -> SimulationFileMetadata | None:
    match = match_simulation_filename(filename)
    if not match:
        return None

    resolved_time_token = match.group("resolved_time")
    return SimulationFileMetadata(
        product_id=match.group("product_id"),
        timestamp=match.group("timestamp"),
        time_step=float(match.group("time_step")),
        time_step_token=match.group("time_step"),
        resolved_time=float(resolved_time_token) if resolved_time_token is not None else None,
        resolved_time_token=resolved_time_token,
        algorithm_name=match.group("algorithm"),
    )


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
        raise PreprocessValidationError(f"Invalid resolved time: {value!r}") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise PreprocessValidationError(
            f"Resolved time must be a non-negative finite value: {value!r}"
        )

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
    resolved_time_fallback: float = DEFAULT_RESOLVED_TIME_FALLBACK,
) -> bool:
    if resolved_time is None:
        return True

    if metadata_resolved_time is None:
        return resolved_time == resolved_time_fallback

    return (
        metadata_resolved_time_token in resolved_time_tokens
        or metadata_resolved_time == resolved_time
    )
