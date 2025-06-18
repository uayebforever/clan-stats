from datetime import datetime
from typing import Sequence

from clan_stats.util.time import TimePeriod, TP_1D


def visual_timeperiods(visual_string: str) -> Sequence[TimePeriod]:
    time_periods: list[TimePeriod] = []
    if len(visual_string) > 31:
        raise ValueError("visual string too long")
    start = None
    for day, letter in enumerate(visual_string):
        if letter == "<":
            start = day
        if letter == ">":
            if start is None:
                raise ValueError("Period without starting '<'")
            time_periods.append(TimePeriod.for_range(
                start=datetime.fromisoformat(f"2000-01-01") + start*TP_1D,
                end=datetime.fromisoformat(f"2000-01-01") + (day+1)*TP_1D))
    return time_periods
