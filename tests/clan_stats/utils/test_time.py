from datetime import datetime

import pytest

from clan_stats.util.itertools import only, first, is_empty, maybe_first
from clan_stats.util.time import *
from randomdata import random_datetime
from visual_time import visual_timeperiods


def test_format_time_as_delta():
    earlier = datetime(2000, 1, 20, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    base = datetime(2000, 1, 20, 12, 0, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    later = datetime(2000, 1, 20, 14, 0, 0, 0, tzinfo=timezone(timedelta(hours=5)))

    assert format_time_delta(earlier - base) == "Today"
    assert format_time_delta(later - base) == "Today"

    assert format_time_delta(
        datetime(2000, 1, 21, 14, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "Tomorrow"
    assert format_time_delta(
        datetime(2000, 1, 19, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "Yesterday"

    assert format_time_delta(
        datetime(2000, 1, 22, 14, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "This Week"
    assert format_time_delta(
        datetime(2000, 1, 18, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "Past Week"

    assert format_time_delta(
        datetime(1999, 12, 25, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "26 days ago"

    assert format_time_delta(
        datetime(1999, 10, 18, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "3 months 4 days ago"

    assert format_time_delta(
        datetime(1998, 10, 18, 10, 0, 0, 0, tzinfo=timezone(timedelta(hours=5))) - base) == "1 year 3 months ago"


class TestTimePeriod:

    @pytest.fixture(scope='class')
    def tp(self) -> TimePeriod:
        start = datetime.fromisoformat("2020-01-01")
        end = datetime.fromisoformat("2020-01-02")

        return TimePeriod.for_range(start, end)

    def test_contains(self):
        before = datetime.fromisoformat("2019-01-01")
        start = datetime.fromisoformat("2020-01-01")
        contained = datetime.fromisoformat("2020-01-20")
        end = datetime.fromisoformat("2020-01-31")
        after = datetime.fromisoformat("2020-02-10")

        tp = TimePeriod.for_range(start, end)

        assert tp.contains(contained)
        assert not tp.contains(before)
        assert not tp.contains(after)

        assert tp.contains(start)
        assert not tp.contains(end)

    def test_overlaps_start(self, tp: TimePeriod):
        other = TimePeriod(start=tp.start - tp.length / 10, length=tp.length)
        assert tp.overlaps(other)
        assert other.overlaps(tp)

    def test_overlaps_at_start(self, tp: TimePeriod):
        other = TimePeriod.for_range(start=tp.start, end=tp.end - tp.length / 10)
        assert tp.overlaps(other)
        assert other.overlaps(tp)

    def test_overlaps_end(self, tp: TimePeriod):
        other = TimePeriod(start=tp.end - tp.length / 10, length=tp.length)
        assert tp.overlaps(other)
        assert other.overlaps(tp)

    def test_overlaps_at_end(self, tp: TimePeriod):
        other = TimePeriod.for_range(start=tp.start + tp.length / 10, end=tp.end)
        assert tp.overlaps(other)
        assert other.overlaps(tp)

    def test_overlaps_adjacent(self, tp: TimePeriod):
        other = TimePeriod(start=tp.end, length=tp.length)
        assert not tp.overlaps(other)
        assert not other.overlaps(tp)

    def test_overlaps_all(self, tp: TimePeriod):
        other = TimePeriod.for_range(start=tp.start + tp.length / 10, end=tp.end - tp.length / 10)
        assert tp.overlaps(other)
        assert other.overlaps(tp)

    def test_overlaps_smaller(self, tp: TimePeriod):
        assert tp.overlaps(
            TimePeriod.for_range(start=tp.start - tp.length / 10,
                                 end=tp.end + tp.length / 10))

    def test_overlaps_same(self, tp: TimePeriod):
        assert tp.overlaps(tp)

    def test_overlaps_none(self, tp: TimePeriod):
        assert not tp.overlaps(TimePeriod(start=tp.end + TP_1h, length=tp.length))

    def _check_difference(self, first: str, secnd: str, befor: str, after: str):
        result = only(visual_timeperiods(first)).difference(
            only(visual_timeperiods(secnd))
        )

        before_periods = maybe_first(visual_timeperiods(befor))
        after_periods = maybe_first(visual_timeperiods(after))

        assert result == (before_periods, after_periods)

    def test_difference_no_overlap(self):
        self._check_difference(
            "  <==>",
            "       <====>",
            "  <==>",
            "",
        )
        self._check_difference(
            "       <====>",
            "  <==>",
            "",
            "       <====>",
        )

    def test_difference_start_overlap(self):
        self._check_difference(
            "     <=====>      ",
            "  <====>          ",
            "",
            "        <==>",
        )
        self._check_difference(
            "     <=====>      ",
            "     <=>          ",
            "",
            "        <==>",
        )
        self._check_difference(
            "     <=====>      ",
            "  <========>      ",
            "",
            ""
        )

    def test_difference_end_overlap(self):
        self._check_difference(
            "     <=====>      ",
            "          <====>          ",
            "     <===>",
            ""
        )
        self._check_difference(
            "     <=========>      ",
            "          <====>          ",
            "     <===>",
            ""
        )
        self._check_difference(
            "     <=========>      ",
            "     <==========>          ",
            "",
            ""
        )


    def test_difference_middle_overlap(self, tp: TimePeriod):
        self._check_difference(
            "  <===========>      ",
            "      <====>          ",
            "  <==>",
            "            <=>"
        )


    def test_combine_contiguous(self, tp: TimePeriod):
        # same
        assert tp.combine_contiguous(TimePeriod(start=tp.start, length=tp.length)) == tp

        # after
        assert (tp.combine_contiguous(TimePeriod(start=tp.end, length=tp.length))
                == TimePeriod.for_range(tp.start, tp.end + tp.length))

        # before
        assert (tp.combine_contiguous(TimePeriod.for_range(tp.start - tp.length, end=tp.start))
                == TimePeriod.for_range(tp.start - tp.length, tp.end))

        # larger
        assert (tp.combine_contiguous(TimePeriod.for_range(tp.start - tp.length, end=tp.end + tp.length))
                == TimePeriod.for_range(tp.start - tp.length, tp.end + tp.length))

        # smaller
        assert (tp.combine_contiguous(TimePeriod.for_range(tp.start + tp.length / 10, tp.end - tp.length / 10))
                == tp)

        # non contiguous
        with pytest.raises(ValueError):
            tp.combine_contiguous(TimePeriod(start=tp.end + TP_1h, length=tp.length))
