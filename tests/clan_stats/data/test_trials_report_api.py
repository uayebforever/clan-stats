import pytest

from clan_stats.data.trials_report_api import search_players
from clan_stats.util.itertools import not_empty


@pytest.mark.asyncio
async def test_search_players():

    result = await search_players("forever")

    assert not_empty(result)