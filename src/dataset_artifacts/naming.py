from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re


TIME_STEP_RE_FRAGMENT = r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?"
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
class PreprocessedFilenameMetadata:
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str


@dataclass(frozen=True)
class SimulationFilenameMetadata:
    product_id: str
    timestamp: str
    time_step: float
    time_step_token: str
    resolved_time: float | None
    resolved_time_token: str | None
    algorithm_name: str


def _format_positive_decimal(value: float | str | Decimal, *, field_name: str) -> str:
    try:
        decimal_value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"Invalid {field_name}: {value!r}") from error

    if not decimal_value.is_finite() or decimal_value <= 0:
        raise ValueError(f"{field_name} must be a positive finite value: {value!r}")

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def format_time_step(time_step: float | str | Decimal) -> str:
    return _format_positive_decimal(time_step, field_name="time step")


def format_resolved_time(resolved_time: float | str | Decimal) -> str:
    try:
        decimal_value = Decimal(str(resolved_time))
    except InvalidOperation as error:
        raise ValueError(f"Invalid resolved time: {resolved_time!r}") from error

    if not decimal_value.is_finite() or decimal_value < 0:
        raise ValueError(
            f"resolved time must be a non-negative finite value: {resolved_time!r}"
        )

    normalized = decimal_value.normalize()
    if normalized == normalized.to_integral():
        return format(normalized, "f")
    return format(normalized, "f").rstrip("0").rstrip(".")


def parse_preprocessed_filename(filename: str) -> PreprocessedFilenameMetadata | None:
    match = _PREPROCESSED_RE.match(filename)
    if match is None:
        return None
    return PreprocessedFilenameMetadata(
        product_id=match.group("product_id"),
        timestamp=match.group("timestamp"),
        time_step=float(match.group("time_step")),
        time_step_token=match.group("time_step"),
    )


def parse_simulation_filename(filename: str) -> SimulationFilenameMetadata | None:
    match = _SIMULATION_RE.match(filename)
    if match is None:
        return None
    resolved_time_token = match.group("resolved_time")
    return SimulationFilenameMetadata(
        product_id=match.group("product_id"),
        timestamp=match.group("timestamp"),
        time_step=float(match.group("time_step")),
        time_step_token=match.group("time_step"),
        resolved_time=float(resolved_time_token) if resolved_time_token is not None else None,
        resolved_time_token=resolved_time_token,
        algorithm_name=match.group("algorithm"),
    )


def build_preprocessed_output_path(
    output_dir: Path | str,
    product_id: str,
    timestamp: str,
    time_step: float,
) -> Path:
    token = format_time_step(time_step)
    return Path(output_dir) / f"{product_id}-{timestamp}-{token}-orderbook_for_plot.npz"


def build_simulation_output_path(
    output_dir: Path | str,
    product_id: str,
    timestamp: str,
    time_step: float,
    algorithm_name: str,
    resolved_time: float,
) -> Path:
    time_step_token = format_time_step(time_step)
    resolved_time_token = format_resolved_time(resolved_time)
    filename = (
        f"{product_id}-{timestamp}-{time_step_token}-resolved-{resolved_time_token}"
        f"-simulation-{algorithm_name}.npz"
    )
    return Path(output_dir) / filename
