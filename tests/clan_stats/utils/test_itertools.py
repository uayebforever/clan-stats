import pytest

from clan_stats.util.itertools import rest


def test_rest_no_elements():
    with pytest.raises(ValueError):
        rest([])


def test_rest_elements():
    assert list(rest([1,2,3,4])) == [2, 3, 4]
