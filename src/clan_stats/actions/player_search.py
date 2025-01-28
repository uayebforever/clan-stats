import asyncio
import logging
from datetime import timedelta
from typing import Sequence, Tuple

from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import ActivityWithPost, filter_activities_by_date
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player
from clan_stats.terminal import term, MessageType
from clan_stats.util.time import now, days_ago

logger = logging.getLogger(__name__)


def player_search(data_retriever: DataRetriever, search_string: str) -> None:
    players = asyncio.run(_get_data(data_retriever, search_string))

    if len(players) == 0:
        term.print(MessageType.SUMMARY, f"No players found for search '{search_string}'")
        return

    term.print(MessageType.SUMMARY, f"Found {len(players)} players for search '{search_string}'")
    for player in players:
        term.print(MessageType.SECTION, f"{player.name}  ({player.primary_membership.membership_id})")
        if player.all_names is not None:
            for membership_type, name in player.all_names.items():
                term.print(MessageType.TEXT, f"   {membership_type}: {name}")


async def _get_data(data_retriever: DataRetriever, search_string: str) -> Sequence[Player]:
    async with data_retriever:
        players = await data_retriever.find_players(search_string)
    return players
