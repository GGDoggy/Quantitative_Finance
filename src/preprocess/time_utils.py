from __future__ import annotations

import math
from collections.abc import Iterator

import numpy as np


_SECONDS_PER_DAY = 86_400.0
_NANOSECONDS_PER_SECOND = 1_000_000_000


def normalize_event_seconds(event_seconds: np.ndarray) -> np.ndarray:
    seconds = np.asarray(event_seconds, dtype=float)
    if seconds.size == 0:
        return np.array([], dtype=float)

    adjusted = seconds.copy()
    day_offset = 0.0
    previous = float(adjusted[0])
    for index in range(1, len(adjusted)):
        current = float(seconds[index])
        if current < previous:
            day_offset += _SECONDS_PER_DAY
        adjusted[index] = current + day_offset
        previous = current
    return adjusted


def sort_and_normalize_event_seconds(
    event_seconds: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    seconds = np.asarray(event_seconds, dtype=float)
    if seconds.size == 0:
        return np.array([], dtype=float), np.array([], dtype=int)

    order = np.argsort(seconds, kind="stable")
    sorted_seconds = seconds[order]
    if sorted_seconds.size <= 1:
        return sorted_seconds.copy(), order

    forward_gaps = np.diff(sorted_seconds)
    wrap_gap = (sorted_seconds[0] + _SECONDS_PER_DAY) - sorted_seconds[-1]
    gaps = np.concatenate((forward_gaps, np.asarray([wrap_gap], dtype=float)))
    split_index = int(np.argmax(gaps)) + 1
    if split_index >= len(sorted_seconds):
        return sorted_seconds.copy(), order

    rotated_seconds = np.concatenate(
        (
            sorted_seconds[split_index:],
            sorted_seconds[:split_index] + _SECONDS_PER_DAY,
        )
    )
    rotated_order = np.concatenate((order[split_index:], order[:split_index]))
    return rotated_seconds, rotated_order


def event_seconds_to_datetime64(
    event_seconds: np.ndarray,
    day_origin: np.datetime64,
) -> np.ndarray:
    normalized_seconds = normalize_event_seconds(event_seconds)
    if normalized_seconds.size == 0:
        return np.array([], dtype="datetime64[ns]")

    nanos = np.rint(normalized_seconds * _NANOSECONDS_PER_SECOND).astype(
        "timedelta64[ns]"
    )
    return np.asarray(day_origin + nanos, dtype="datetime64[ns]")


def sorted_update_times(update_rows: list[list[float]]) -> np.ndarray:
    if not update_rows:
        return np.array([], dtype=float)
    rows = np.asarray(update_rows, dtype=float)
    if rows.ndim != 2 or rows.shape[1] != 4:
        raise ValueError("Update rows must be a 2D array with columns: time, price, volume, side.")
    normalized, _ = sort_and_normalize_event_seconds(rows[:, 0])
    return normalized


def compute_trimmed_window(
    anchor_times: np.ndarray,
    update_times: np.ndarray,
) -> tuple[float, float] | None:
    if anchor_times.size == 0 or update_times.size == 0:
        return None

    anchor_start = float(np.min(anchor_times))
    anchor_end = float(np.max(anchor_times))
    update_start = float(np.min(update_times))
    update_end = float(np.max(update_times))
    common_start = max(anchor_start, update_start)
    common_end = min(anchor_end, update_end)
    trimmed_start = common_start + 1.0
    trimmed_end = common_end - 1.0
    if trimmed_start >= trimmed_end:
        return None
    return (trimmed_start, trimmed_end)


def iter_bucket_starts(
    trimmed_start: float,
    trimmed_end: float,
    window_seconds: int,
) -> Iterator[float]:
    bucket_start = float(math.ceil(trimmed_start))
    while bucket_start + window_seconds <= trimmed_end:
        yield bucket_start
        bucket_start += window_seconds
