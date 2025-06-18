# uses backend that stores type of object
# cache for date region
# passes through for requests outside cached region
# multi-key value cache
from datetime import datetime
from typing import TypeAlias
from unittest.mock import Mock

from clan_stats.data.history_cache import ActivityCache, HistoryGetter, TimePeriodTracker
from clan_stats.util.itertools import only, is_empty
from clan_stats.util.time import TimePeriod, TP_1h, TP_1D
from randomdata import random_datetime, random_satisfying
from visual_time import visual_timeperiods


keyType: TypeAlias = tuple[int, str]


def test_get_range_passes_to_delegate_when_not_cached():
    getter = Mock(spec_set=HistoryGetter)

    cache: ActivityCache[keyType, str] = ActivityCache(getter)

    start = datetime.fromisoformat("2020-01-01")
    end = datetime.fromisoformat("2020-02-01")
    key = (123, "abc")
    _ = cache.get_range(key=key, start=start, end=end)

    getter.assert_called_once_with(key=key, start=start, end=end)


def test_has_range_none():
    cache: ActivityCache[keyType, str] = ActivityCache(Mock(spec_set=HistoryGetter))

    start = random_datetime()
    end = random_satisfying(random_datetime, lambda d: d > start)
    key = (123, "abc")

    assert cache.has_range(key, start, end) is False


def test_has_range_after_get():
    cache: ActivityCache[keyType, str] = ActivityCache(Mock(spec_set=HistoryGetter))

    start: datetime = random_datetime()
    end: datetime = random_satisfying(random_datetime, lambda d: d > start)
    key = (123, "abc")

    _ = cache.get_range(key, start, end)
    assert cache.has_range(key, start, end) is True


class TestTimePeriodTracker:

    def test_add_coverage_no_overlap(self):
        tracker = TimePeriodTracker()

        assert is_empty(tracker.get_coverage())

        tp1 = TimePeriod(start=datetime.fromisoformat("2020-01-01"), length=TP_1h)
        tracker.add_coverage(tp1)
        assert only(tracker.get_coverage()) == tp1

        tp2 = TimePeriod(start=datetime.fromisoformat("2020-01-03"), length=TP_1h)
        tracker.add_coverage(tp2)
        assert list(tracker.get_coverage()) == [tp1, tp2]

    def test_add_coverage_with_overlap(self):
        tracker = TimePeriodTracker()

        tp1 = TimePeriod(start=datetime.fromisoformat("2020-01-01"), length=TP_1D)
        tracker.add_coverage(tp1)
        assert only(tracker.get_coverage()) == tp1

        tp2 = TimePeriod(start=tp1.end - TP_1h, length=tp1.length)
        tracker.add_coverage(tp2)
        assert only(tracker.get_coverage()) == TimePeriod.for_range(tp1.start, tp2.end)

    def test_add_coverage_with_overlap_multiple(self):
        tracker = TimePeriodTracker()

        tracker.add_coverage(tp_first := TimePeriod(start=datetime.fromisoformat("2020-01-01"), length=TP_1D))
        second_start = datetime.fromisoformat("2020-01-03")
        tracker.add_coverage(TimePeriod(start=second_start, length=TP_1D))
        tracker.add_coverage(TimePeriod(start=datetime.fromisoformat("2020-01-05"), length=TP_1D))
        second_last_end = datetime.fromisoformat("2020-01-08")
        tracker.add_coverage(TimePeriod.for_range(start=datetime.fromisoformat("2020-01-07"), end=second_last_end))
        tracker.add_coverage(tp_last := TimePeriod(start=datetime.fromisoformat("2020-01-09"), length=TP_1D))

        tracker.add_coverage(TimePeriod.for_range(
            start=second_start + TP_1D / 2,
            end=second_last_end - TP_1D / 2))

        assert tracker.get_coverage() == [
            tp_first, TimePeriod.for_range(start=second_start, end=second_last_end), tp_last
        ]

    def test_add_coverage_with_overlap_all(self):
        tracker = TimePeriodTracker()

        tp1 = TimePeriod(start=datetime.fromisoformat("2020-01-01"), length=TP_1h)
        tracker.add_coverage(tp1)

        tp2 = TimePeriod(start=datetime.fromisoformat("2020-01-03"), length=TP_1h)
        tracker.add_coverage(tp2)

        tp_longest = TimePeriod.for_range(tp1.start - tp1.length / 10, tp2.end + tp2.length / 10)
        tracker.add_coverage(tp_longest)

        assert only(tracker.get_coverage()) == tp_longest

    def test_get_missing_when_no_coverage(self):
        tracker = TimePeriodTracker()

        tp = TimePeriod.for_range(start=datetime.fromisoformat("2020-01-01"),
                                  end=datetime.fromisoformat("2021-01-01"))

        period = only(tracker.get_missing(tp))

        assert period == tp

    def test_get_missing_no_overlap(self):
        self._check_missing(
            "        <=>  <=>  <==> ",
            "  <===>       ",
            "  <===>           "
        )
        self._check_missing(
            "<=>        <=>  <==> ",
            "    <===>       ",
            "    <===>           "
        )

    def test_get_missing_overlap_first(self):
        self._check_missing(
            "  <=>  <=>  <==> ",
            "  <======>       ",
            "     <>           "
        )
        self._check_missing(
            "  <=>  <=>  <==> ",
            "<========>       ",
            "<>   <>           "
        )
        self._check_missing(
            "  <=>  <=>   <==> ",
            "<==========>       ",
            "<>   <>   <>        "
        )

    def test_get_missing_multiple_overlap(self):
        self._check_missing(
            "  <=>  <=>  <==> ",
            "  <==========>       ",
            "     <>   <>        "
        )
        self._check_missing(
            "  <=>  <=>  <==> ",
            "<================>",
            "<>   <>   <>    <>"
        )


    def _check_missing(self, cover: str, check: str, expec: str):
        tracker = TimePeriodTracker()
        for period in visual_timeperiods(cover):
            tracker.add_coverage(period)
        missing = tracker.get_missing(only(visual_timeperiods(check)))

        assert missing == visual_timeperiods(expec)

