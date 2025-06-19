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

def activity_summary(data_retriever: DataRetriever, player_id: int, days: int = 30):
    player, clan, manifest, activities_with_post = asyncio.run(_get_data(data_retriever, player_id,
                                                                         days))

    clan_member_ids = _clan_member_ids_without_player(clan, player)

    term.print(MessageType.SUMMARY, f"Player activity report for {player.name}")

    for activity in sorted(activities_with_post, key=lambda a: a.time_period.start):
        teammates = list(p for p in activity.players if p.primary_membership != player.primary_membership)
        logger.debug(activity)
        activity_is_with_clanmates = True \
            if len(set(p.primary_membership for p in activity.players).intersection(clan_member_ids)) > 0 \
            else False
        term.print_activity_summary(activity, manifest, teammates, clanmates=activity_is_with_clanmates)


async def _get_data(data_retriever: DataRetriever, player_id: int, days: int) -> Tuple[
    Player, Clan, Manifest, Sequence[ActivityWithPost]]:
    async with data_retriever:
        player = await data_retriever.get_player(player_id)
        logger.debug("Minimal player for given player id %s", player)
        clan = await data_retriever.get_clan_for_player(player)
        manifest = await data_retriever.get_manifest()
        ago = days_ago(days)
        activities = await data_retriever.get_activities_for_player(
            player,
            min_start_date=ago)

        logger.debug("Limiting to %s", ago)
        activities_with_post = await asyncio.gather(*[data_retriever.get_post_for_activity(a)
            for a in filter_activities_by_date(activities, ago)])

    return player, clan, manifest, activities_with_post


def _clan_member_ids_without_player(clan, player):
    clan_member_ids = set(p.primary_membership for p in clan.players)
    clan_member_ids.remove(player.primary_membership)
    return clan_member_ids
