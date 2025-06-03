from datetime import datetime
from typing import Optional, Callable, Sequence

from clan_stats.data._bungie_api.bungie_types import DestinyHistoricalStatsPeriodGroup
from clan_stats.util.itertools import first


def activity_history_to(start_date: Optional[datetime]) -> Optional[Callable[[list], bool]]:
    if start_date is None:
        return None

    def enough(activities: Sequence[DestinyHistoricalStatsPeriodGroup]) -> bool:
        return _time_of_oldest_activity(activities) < start_date

    return enough


def _time_of_oldest_activity(activities: Sequence[DestinyHistoricalStatsPeriodGroup]) -> datetime:
    return first(sorted(activities, key=_activity_time)).period


def _activity_time(activity: DestinyHistoricalStatsPeriodGroup) -> datetime:
    return activity.period
