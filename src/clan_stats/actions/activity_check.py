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
from clan_stats.ui.lists import print_member_list, print_player_list
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

    # if sort_by == "name":
    #     def name_key(player: MinimalPlayer):
    #         return player.name.lower()
    #
    #     sorted_players = list(sorted(found, key=name_key))
    # elif sort_by == "active":
    #     sorted_players = _sort_by_last_active(found, last_active)
    # elif sort_by == "discord":
    #     def discord_sort_key(player: MinimalPlayer) -> str:
    #         return clan_database.get_discord_name(player.primary_membership.membership_id).lower()
    #     sorted_players = list(sorted(found, key=discord_sort_key))
    # else:
    #     raise ValueError(f"Sort option {sort_by} unknown")

    term.print(MessageType.TEXT,
               f"Total members: {len(list(clan_database.current_members()))}, players in the bungie clan: {len(clan.players)}  ")

    print_member_list(
        found,
        description="Members found in Bungie Clan ({count}):")

    if not_empty(missing):
        term.skip()
        print_member_list(
            missing,
            description="Members not in Bungie Clan ({count}):")

    if not_empty(new_unknown):
        term.skip()
        print_player_list(
            new_unknown,
            description="Players in Bungie Clan not found in current memberships: ({count})")


def _find_discrepancies(clan: Clan, clan_database: ClanMembershipDatabase
                        ) -> Tuple[Sequence[Member], Sequence[Member], Sequence[GroupMinimalPlayer]]:
    differences = find_differences(
        clan_database.current_members(), lambda m: only(m.active_accounts(AccountType.BUNGIE)).account_identifier,
        clan.players, lambda p: str(p.primary_membership.membership_id),
    )
    new_unknown = differences.in_second
    found = differences.in_both
    missing = differences.in_first
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
