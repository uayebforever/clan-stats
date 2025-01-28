import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum
from typing import Tuple, Mapping, Sequence, Optional, Any

from aiobungie import GameMode
from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import Activity
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import MinimalPlayer
from clan_stats.discord import DiscordGroup
from clan_stats.terminal import term
from clan_stats.util.async_utils import collect_map


def clears(clan_id: int,
           discord_group: DiscordGroup,
           data_retriever: DataRetriever,
           sort_by: str = "name"):
    clan, raid_data, manifest = asyncio.run(_fetch_clan_raid_data(data_retriever, clan_id))

    raid_counts = {player_name: _raid_counts(raids, manifest) for player_name, raids in raid_data.items()}

    if sort_by == "name":
        def sort_key(i: Tuple[str, Mapping[Raid, int]]):
            return i[0].lower()
    elif sort_by == "count":
        def sort_key(i: Tuple[str, Mapping[Raid, int]]):
            return sum(i[1].values()) if i[1] is not None else 0
    else:
        raise KeyError(f"Invalid sort by '{sort_by}'")

    tabulated_counts = [
        ([p] + [counts[r] for r in Raid.current()] + [sum(counts.values())]
         if counts
         else [p] + ["-" for r in Raid.current()] + ["-"])
        for p, counts in sorted(raid_counts.items(), key=sort_key)
    ]
    headings = [""] + [r.name for r in Raid] + ["Total"]

    term.print_table(headings, tabulated_counts)


class Raid(StrEnum):
    SE = "Salvation's Edge"
    CROTA = "Crota's End"
    ROOT = "Root of Nightmares"
    KF = "King's Fall"
    VOW = "Vow of the Disciple"
    VOG = "Vault of Glass"
    DSC = "Deep Stone Crypt"
    GOS = "Garden of Salvation"
    LW = "Last Wish"
    LEV = "Leviathan"
    PAN = "Pantheon"
    COS = "Crown of Sorrow"
    SOTP = "Scourge of the Past"
    UNKNOWN = "Unknown?"

    @classmethod
    def current(cls) -> Sequence['Raid']:
        return [cls.SE, cls.CROTA, cls.ROOT, cls.KF, cls.VOW, cls.VOG, cls.DSC, cls.GOS, cls.LW]

    @classmethod
    def from_director_activity_hash(cls, dah: int, manifest: Manifest) -> 'Raid':
        activity_name = manifest.get_activity_name(dah)
        for raid in cls.__members__.values():
            if raid.value in activity_name:
                return raid
            elif dah in (4103176774,):
                return cls.UNKNOWN
        raise KeyError(f"Unknown raid hash {dah} mapping to {activity_name}")


async def _fetch_clan_raid_data(
        data_retriever: DataRetriever,
        clan_id: int
) -> Tuple[Clan, Mapping[str, Optional[Sequence[Activity]]], Manifest]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        raid_data = await _get_raids(data_retriever, clan.players)
        manifest = await data_retriever.get_manifest()

    return clan, raid_data, manifest


async def _get_raids(data_retriever: DataRetriever,
                     players: Sequence[MinimalPlayer]
                     ) -> Mapping[str, Optional[Sequence[Activity]]]:
    player_raids = await collect_map(
        {p.name: data_retriever.get_activities_for_player(
            p, mode=GameMode.RAID, min_start_date=datetime(year=2022, month=1, day=1, tzinfo=timezone.utc))
            for p in players})
    return player_raids


def _raid_counts(raids: Optional[Sequence[Activity]],
                 manifest: Optional[Manifest] = None
                 ) -> Optional[Mapping[Raid, int]]:
    result = defaultdict(lambda: 0)

    if raids is None:
        return None

    for activity in raids:
        raid = Raid.from_director_activity_hash(activity.director_activity_hash, manifest)
        if activity.completed is True:
            result[raid] += 1

    return result
