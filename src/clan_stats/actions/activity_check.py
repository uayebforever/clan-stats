import asyncio
from datetime import datetime, timezone
from typing import List, Tuple, Mapping, Sequence, Optional

from aiobungie import GameMode
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import Activity
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, MinimalPlayer, GroupMinimalPlayer
from clan_stats.discord import DiscordGroup
from clan_stats.terminal import term, MessageType
from clan_stats.util.async_utils import collect_map
from clan_stats.util.optional import require_else


def activity_summary(clan_id: int,
                     discord_group: DiscordGroup,
                     data_retriever: DataRetriever,
                     sort_by: str = "name",
                     activity_mode: GameMode = GameMode.NONE):
    clan, last_active = asyncio.run(_fetch_clan_data(data_retriever, clan_id, activity_mode))

    found, missing = _not_in_discord(clan, discord_group)

    if sort_by == "name":
        def name_key(player: MinimalPlayer):
            return player.name.lower()

        sorted_players = list(sorted(found, key=name_key))
    elif sort_by == "active":
        sorted_players = _sort_by_last_active(found, last_active)
    elif sort_by == "discord":
        def discord_sort_key(player: MinimalPlayer):
            return discord_group.get_discord(player.name).lower()

        sorted_players = list(sorted(found, key=discord_sort_key))
    else:
        raise ValueError(f"Sort option {sort_by} unknown")

    term.print(MessageType.TEXT,
               f"Bungie clan members: {len(clan.players)}  Discord members: {len(discord_group.members)}")

    term.print(MessageType.TEXT, "Bungie Clan Members")
    for i, player in enumerate(sorted_players):
        term.print_player_line(player,
                               discord_name=discord_group.get_discord(player.name),
                               last_active=last_active[player.name],
                               index=i)

    if len(found) < len(discord_group.members):
        term.skip()
        term.warning("There is at least one discord member that was not found in the Bungie clan list!!!")
        mismatch = set(m.charlemagne_name for m in discord_group.members) - set(p.name for p in clan.players)
        for name in sorted(mismatch):
            print(f"   {name} / @{discord_group.get_discord(name)}")

    print(f"\nMissing players: ({len(missing)})")
    for player in sorted(missing, key=lambda x: x.primary_membership.membership_id):
        if isinstance(player, GroupMinimalPlayer):
            join_date = "Joined " + player.group_join_date.strftime("%-d %B %Y")
        else:
            join_date = None
        term.print_player_line(player, discord_name=join_date)


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


def _not_in_discord(clan: Clan, discord_group: DiscordGroup) -> Tuple[List[Player], List[Player]]:
    discord = {d.charlemagne_name for d in discord_group.members}
    bungie = {p.name for p in clan.players}

    missing = [clan.player_by_name(n) for n in bungie - discord]
    found = [clan.player_by_name(n) for n in bungie.intersection(discord)]
    return found, missing
