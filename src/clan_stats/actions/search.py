import asyncio
import logging
from typing import Sequence

from clan_stats.data import trials_report_api
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.individuals import Player
from clan_stats.terminal import term, MessageType

logger = logging.getLogger(__name__)


async def trials_report_player_search(data_retriever: DataRetriever, search_string: str) -> None:
    players = await trials_report_api.search_players(search_string)

    players = await asyncio.gather(*[
        data_retriever.get_player(int(p.membershipId)) for p in players])

    print_players(players, search_string)


def bungie_player_search(data_retriever: DataRetriever, search_string: str) -> None:
    players = asyncio.run(_get_data(data_retriever, search_string))

    if len(players) == 0:
        term.print(MessageType.SUMMARY, f"No players found for search '{search_string}'")
        return

    print_players(players, search_string)


def print_players(players: Sequence[Player], search_string: str) -> None:
    term.print(MessageType.SUMMARY, f"Found {len(players)} players for search '{search_string}'")
    for player in players:
        term.print(MessageType.TEXT, f"{player.name}  ({player.primary_membership.membership_id})")

        if player.all_memberships is not None:
            for platform, membership in player.all_memberships.items():
                term.print(MessageType.TEXT,
                           f"   {platform} ({membership.cross_save_status.single_letter()}): "
                           + f"{membership.platform_display_name}")


async def _get_data(data_retriever: DataRetriever, search_string: str) -> Sequence[Player]:
    async with data_retriever:
        players = await data_retriever.find_players(search_string)
    return players

def clan_search(data_retriever: DataRetriever, search_string: str) -> None:
    clans_found = asyncio.run(data_retriever.find_clans(search_string))

    for clan in clans_found:
        print(clan.name, clan.id)
