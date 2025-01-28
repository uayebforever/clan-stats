import pytest

from clan_stats.terminal import _batch


@pytest.mark.parametrize("seq,expected",
                         [
                             ((1, 2, 3, 4, 5), [[1, 2, 3], [4, 5]]),
                             ((1, 2, 3, 4, ), [[1, 2, 3], [4]]),
                             ((1, 2, 3, 4, 5, 6), [[1, 2, 3], [4, 5, 6]]),
                         ])
def test_batch(seq, expected):
    assert list(_batch(seq, size=3)) == expected


@pytest.mark.parametrize("seq,expected",
                         [
                             ((1, 2, 3, 4, 5), [[1, 2, 3], [4, 5, 0]]),
                             ((1, 2, 3, 4, ), [[1, 2, 3], [4, 0, 0]]),
                             ((1, 2, 3, 4, 5, 6), [[1, 2, 3], [4, 5, 6]]),
                         ])
def test_batch_padding(seq, expected):
    assert list(_batch(seq, size=3, pad=0)) == expected
