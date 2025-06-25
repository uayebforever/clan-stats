import asyncio
from datetime import datetime, timezone
from typing import Tuple, Mapping, Sequence, Optional

from aiobungie import GameMode
from clan_stats.clan_manager import ClanMembershipDatabase, AccountType, Member
from clan_stats.clan_manager.membership_database import MembershipDatabase
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import Activity
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import MinimalPlayer, GroupMinimalPlayer
from clan_stats.terminal import term, MessageType
from clan_stats.util.async_utils import collect_map
from clan_stats.util.itertools import not_empty, only
from clan_stats.util.optional import require_else, require
from clan_stats.util.set_helpers import find_differences


def activity_summary(clan_id: int,
                     data_retriever: DataRetriever,
                     sort_by: str = "name",
                     activity_mode: GameMode = GameMode.NONE):
    clan, last_active = asyncio.run(_fetch_clan_data(data_retriever, clan_id, activity_mode))

    clan_database = ClanMembershipDatabase(MembershipDatabase(ClanMembershipDatabase.path(clan_id)))

    found, missing, new_unknown = _find_discrepancies(clan, clan_database)

    if sort_by == "name":
        def name_key(player: MinimalPlayer):
            return player.name.lower()

        sorted_players = list(sorted(found, key=name_key))
    elif sort_by == "active":
        sorted_players = _sort_by_last_active(found, last_active)
    elif sort_by == "discord":
        def discord_sort_key(player: MinimalPlayer) -> str:
            return clan_database.get_discord_name(player.primary_membership.membership_id).lower()

        sorted_players = list(sorted(found, key=discord_sort_key))
    else:
        raise ValueError(f"Sort option {sort_by} unknown")

    term.print(MessageType.TEXT,
               f"Total members: {len(list(clan_database.current_members()))}, players in the bungie clan: {len(clan.players)}  ")

    term.print(MessageType.TEXT, "Members found in Bungie Clan")
    for i, player in enumerate(sorted_players):
        term.print_player_line(player,
                               discord_name=clan_database.get_discord_name(player.primary_membership.membership_id),
                               last_active=last_active[player.name],
                               index=i + 1)

    if not_empty(missing):
        term.skip()
        term.warning("Members not in bungie clan:")
        for member in sorted(missing, key=lambda m: require(m.bungie_name())):
            term.print(MessageType.TEXT, f"   {member.bungie_name()} / @{member.discord_name()}")

    term.print(MessageType.TEXT, f"\nPlayers in bungie clan not found in membership database: ({len(new_unknown)})")
    for player in sorted(new_unknown, key=lambda x: x.primary_membership.membership_id):
        join_date = "Joined " + player.group_join_date.strftime("%-d %B %Y")
        term.print_player_line(player, discord_name=join_date)


def _find_discrepancies(clan: Clan, clan_database: ClanMembershipDatabase
                        ) -> Tuple[Sequence[GroupMinimalPlayer], Sequence[Member], Sequence[GroupMinimalPlayer]]:
    differences = find_differences(
        clan.players, lambda p: str(p.primary_membership.membership_id),
        clan_database.current_members(), lambda m: only(m.active_accounts(AccountType.BUNGIE)).account_identifier,
    )
    new_unknown = differences.in_first
    found = differences.in_both
    missing = differences.in_second
    return found, missing, new_unknown


def _sort_by_last_active(players: Sequence[MinimalPlayer],
                         last_active: Mapping[str, Optional[datetime]]
                         ) -> Sequence[MinimalPlayer]:
    def last_active_key(player: MinimalPlayer) -> datetime:
        return require_else(last_active[player.name], datetime.fromtimestamp(0, timezone.utc))

    return list(sorted(players, key=last_active_key))


async def _get_most_recently_active(player_activities: Mapping[str, Optional[Sequence[Activity]]]
                                    ) -> Mapping[str, Optional[datetime]]:
    result = {}
    for name, activities in player_activities.items():
        if activities is None or len(activities) == 0:
            result[name] = None
        else:
            result[name] = max(a.time_period.start for a in activities)
    return result


async def _fetch_clan_data(data_retriever: DataRetriever, clan_id: int, mode: GameMode = GameMode.NONE
                           ) -> Tuple[Clan, Mapping[str, Optional[datetime]]]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        last_active = await get_most_recent_activity(data_retriever, clan.players, mode=mode)
    return clan, last_active


async def get_most_recent_activity(data_retriever: DataRetriever,
                                   players: Sequence[MinimalPlayer],
                                   mode: GameMode = GameMode.NONE
                                   ) -> Mapping[str, Optional[datetime]]:
    player_activities = await collect_map({p.name: data_retriever.get_activities_for_player(p, mode=mode)
                                           for p in players})
    return await _get_most_recently_active(player_activities)
