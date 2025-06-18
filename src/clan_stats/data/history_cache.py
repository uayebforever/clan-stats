from abc import ABCMeta, abstractmethod, ABC
from datetime import datetime
from typing import Protocol, Optional
from typing import TypeVar, Generic, Any, Sequence

from clan_stats.util.itertools import is_empty, not_empty
from clan_stats.util.optional import require_else, map_optional
from clan_stats.util.time import TimePeriod

_T_key = TypeVar('_T_key', bound=tuple[Any, ...])
_T_key_contra = TypeVar('_T_key_contra', bound=tuple[Any, ...], contravariant=True)

_R = TypeVar('_R')
_R_cov = TypeVar('_R_cov', covariant=True)


class TimestampKey(Generic[_T_key]):
    pass


class Storage(ABC, Generic[_T_key, _R]):

    @abstractmethod
    def read(self, key: _T_key) -> _R:
        raise NotImplementedError

    @abstractmethod
    def write(self, key: _T_key, value: _R) -> None:
        raise NotImplementedError


class TimePeriodTracker:

    def __init__(self):
        self._coverage: list[TimePeriod] = []

    def get_missing(self, check_period: TimePeriod) -> Sequence[TimePeriod]:
        for covered_period in self._coverage:
            if covered_period.overlaps(check_period):
                return self._calculate_differences(check_period)
        return [check_period]

    def covers(self, timestamp: datetime) -> bool:
        for period in self._coverage:
            if period.contains(timestamp):
                return True
        return False

    def get_coverage(self) -> Sequence[TimePeriod]:
        return sorted(self._coverage, key=lambda tp: tp.start)

    def add_coverage(self, new_period: TimePeriod):
        new_coverage: list[TimePeriod] = []
        expanded_previous: Optional[TimePeriod] = None
        added = False
        for period in self.get_coverage():
            current_period = require_else(expanded_previous, new_period)
            if not current_period.overlaps(period):
                if expanded_previous is not None:
                    new_coverage.append(expanded_previous)
                    expanded_previous = None
                new_coverage.append(period)
                continue
            added = True
            expanded_previous = current_period.combine_contiguous(period)
        if expanded_previous is not None:
            new_coverage.append(expanded_previous)
        if not added:
            new_coverage.append(new_period)
        self._coverage = new_coverage

    def _calculate_differences(self, check_period: TimePeriod) -> Sequence[TimePeriod]:
        missing_periods: list[TimePeriod] = []

        for period in self.get_coverage():
            if check_period.overlaps(period):
                result = check_period.difference(period)
                map_optional(result.before, missing_periods.append)
                if result.after is None:
                    return missing_periods
                else:
                    check_period = result.after
        missing_periods.append(check_period)
        return missing_periods

class HistoryGetter(Protocol[_T_key_contra, _R_cov]):
    def __call__(self, key: _T_key_contra, start: datetime, end: datetime) -> Sequence[_R_cov]: ...


class ActivityCache(Generic[_T_key, _R]):

    def __init__(self, getter: HistoryGetter[_T_key, _R]):
        self._cache_getter: HistoryGetter[_T_key, _R] = getter
        self._upstream_getter: HistoryGetter[_T_key, _R] = getter
        self._trackers: dict[_T_key, TimePeriodTracker] = {}

    def get(self, key: _T_key, earliest: datetime, latest: Optional[datetime] = None) -> Sequence[_R]:
        time_period = TimePeriod.for_range(earliest, require_else(latest, datetime.now()))

        missing_data = self._trackers[key].get_missing(time_period)

        if not_empty(missing_data):
            data = self._upstream_getter(key, time_period.start, time_period.end)

        for datum in data:
            if


        return self._getter(key=key, start=start, end=end)

