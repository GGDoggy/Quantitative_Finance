from __future__ import annotations

import calendar
from datetime import datetime


def parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d.%H%M%S")


def file_time_to_unix(file_time: str) -> int:
    seconds = parse_timestamp(file_time).timetuple()
    return calendar.timegm(seconds)
