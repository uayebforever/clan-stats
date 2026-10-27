from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from clan_stats.data._bungie_api.bungie_enums import CharacterType, MembershipType
from clan_stats.data.retrieval.bungio_data_retriever import BungioDataRetriever
from clan_stats.data.types.individuals import Character, Membership, MinimalPlayer

_NEWEST = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _history_entry(instance_id: int, period: datetime) -> dict:
    return {
        "period": period.isoformat(),
        "activityDetails": {
            "directorActivityHash": 2381413764,
            "instanceId": instance_id,
            "mode": 4,
            "modes": [7, 4],
        },
        "values": {
            "timePlayedSeconds": {"statId": "timePlayedSeconds",
                                  "basic": {"value": 3600.0, "displayValue": "1h"}},
            "completed": {"statId": "completed", "basic": {"value": 1.0, "displayValue": "Yes"}},
        },
    }


def _paged_history(n_pages: int, page_size: int = 3):
    """Activity history pages, newest first, one day per activity, followed by an empty page."""
    pages = [{"activities": [_history_entry(page * page_size + i, _NEWEST - timedelta(days=page * page_size + i))
                             for i in range(page_size)]}
             for page in range(n_pages)]

    async def get_activity_history(page: int, **kwargs):
        return pages[page] if page < len(pages) else {}

    return get_activity_history


@pytest.fixture
def player() -> MinimalPlayer:
    return MinimalPlayer(primary_membership=Membership(membership_id=1, membership_type=MembershipType.PSN),
                         name="test#0001")


@pytest.fixture
def retriever(player) -> BungioDataRetriever:
    retriever = BungioDataRetriever(api_key="")
    retriever.get_characters_for_player = AsyncMock(return_value=[
        Character(membership=player.primary_membership, character_id=2, character_type=CharacterType.HUNTER,
                  power_level=2000, player=player)])
    return retriever


class TestBungioActivityHistory:

    async def test_fetches_pages_back_to_min_start_date(self, retriever, player):
        retriever._client.api.get_activity_history = AsyncMock(side_effect=_paged_history(n_pages=5))

        activities = await retriever.get_activities_for_player(player, min_start_date=_NEWEST - timedelta(days=7))

        # Pages hold 3 days each, so reaching back 7 days needs the first three pages.
        assert len(activities) == 9
        assert retriever._client.api.get_activity_history.await_count == 3

    async def test_stops_at_end_of_history(self, retriever, player):
        retriever._client.api.get_activity_history = AsyncMock(side_effect=_paged_history(n_pages=2))

        activities = await retriever.get_activities_for_player(player, min_start_date=_NEWEST - timedelta(days=900))

        assert len(activities) == 6
