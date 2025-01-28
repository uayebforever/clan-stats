import asyncio
from datetime import timedelta, datetime, timezone
from logging import getLogger
from typing import Sequence, Set, Tuple, Optional, Mapping

from clan_stats.actions.activity_check import get_most_recent_activity
from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, MinimalPlayer
from clan_stats.event.fireteams import SharedFireteamFinder
from clan_stats.fireteams import Fireteam
from clan_stats.terminal import term, MessageType
from clan_stats.util.async_utils import collect_map
from clan_stats.util.time import format_time_weekday_and_time

log = getLogger(__name__)


def recent_clan_fireteams_summary(data_retriever: DataRetriever,
                                  clan_id: int,
                                  recency_days: int = 30,
                                  min_clan_fireteam_members=2):
    recency_limit = datetime.now(timezone.utc) - timedelta(days=recency_days)

    clan, players_in_range, shared_fireteams, last_active, manifest \
        = asyncio.run(_get_data(data_retriever, clan_id, recency_limit, min_clan_fireteam_members))

    term.print(MessageType.SECTION, f"Clan Fireteam report for {clan.name}")

    term.print(MessageType.SECTION, "Bungie Clan Members active in the time range:")
    for player in sorted(players_in_range):
        term.print_player_line(player, last_active=last_active[player.name])

    term.print(MessageType.TEXT, f"\n\nThere were {len(shared_fireteams)} found:")

    for fireteam in sorted(shared_fireteams, key=lambda f: f.activity.time_period.start):
        log.info(fireteam)
        term._print("{activity_name:40s} {time:25s}   {team}".format(
            activity_name=manifest.get_activity_name(fireteam.activity.director_activity_hash),
            time=format_time_weekday_and_time(fireteam.activity.time_period.start),
            team=", ".join(fireteam.member_names)))

    fireteam_participants: Set[str] = set()
    for fireteam in shared_fireteams:
        fireteam_participants.update(fireteam.member_names)

    term.print(MessageType.SECTION, f"{len(fireteam_participants)} members participated in clan fireteams:")
    term.print_columnar_list(fireteam_participants)

    non_fireteam_participants = {p.name for p in clan.players}.difference(fireteam_participants).intersection(p.name for p in players_in_range)
    term.print(MessageType.SECTION, f"{len(non_fireteam_participants)} Clan members who have not joined a clan fireteam but were active")
    term.print_columnar_list(
        non_fireteam_participants)

    inactive = {p.name for p in clan.players}.difference(p.name for p in players_in_range)
    term.print(MessageType.SECTION, f"{len(inactive)} Clan members who weren't active")
    term.print_columnar_list(
        inactive)


async def _get_data(
        data_retriever: DataRetriever,
        clan_id: int,
        recency_limit: datetime,
        min_clan_fireteam_members: int
) -> Tuple[Clan, Sequence[MinimalPlayer], Sequence[Fireteam], Mapping[str, Optional[datetime]], Manifest]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        players_in_range: Sequence[MinimalPlayer] = list(
            p
            for p in clan.players
            if p.last_online is not None and p.last_online > recency_limit)

        manifest = await data_retriever.get_manifest()

        last_active = await get_most_recent_activity(data_retriever, players_in_range)

        shared_fireteams = await SharedFireteamFinder(data_retriever).shared_fireteams(
            players_in_range,
            recency_limit=recency_limit,
            min_size=min_clan_fireteam_members)

    return clan, players_in_range, shared_fireteams, last_active, manifest


def is_activity_with_clanmates(activity, player, clan):
    teammates = list(p for p in activity.post_activity.players if p.member_id != player.member_id)
    activity_member_ids = set(p.member_id for p in activity.post_activity.players)
    clan_member_ids = (p.member_id for p in clan.players)
    return len(activity_member_ids.intersection(clan_member_ids)) > 0
