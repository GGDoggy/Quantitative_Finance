"""Internal transitional re-export facade for legacy preprocess helpers."""
from __future__ import annotations

import calendar
import time

from .io import build_context, build_trade_arrays, read_csv_rows
from .models import PreprocessContext, RawBatchLike


def file_time_to_unix(file_time: str) -> int:
    seconds = time.strptime(file_time, "%Y%m%d.%H%M%S")
    return calendar.timegm(seconds)
