import itertools
from collections import defaultdict
from datetime import datetime
from types import TracebackType
from typing import Mapping, Sequence, Dict, Set, TypeVar, Iterator, Iterable, AsyncContextManager, Type
from logging import getLogger

from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.individuals import Player, MinimalPlayer
from clan_stats.fireteams import Fireteam
from clan_stats.data.types.activities import Activity
from clan_stats.util import async_utils
from clan_stats.util.itertools import first, rest
from clan_stats.util.time import is_tz_aware, TimePeriod

log = getLogger(__name__)


class SharedFireteamFinder(AsyncContextManager):

    def __init__(self, data_retriever: DataRetriever) -> None:
        self._data_retriever: DataRetriever = data_retriever

    async def __aenter__(self):
        return await self._data_retriever.__aenter__()

    async def __aexit__(self,
                        exception_type: Type[BaseException] | None,
                        exception: BaseException | None,
                        traceback: TracebackType | None) -> bool | None:
        return await self._data_retriever.__aexit__()

    async def shared_fireteams(self,
                               players: Iterable[MinimalPlayer],
                               recency_limit: datetime,
                               min_size: int = 2) -> Sequence[Fireteam]:
        if not is_tz_aware(recency_limit):
            raise ValueError

        tasks_by_player_name = {player.name: self.get_recency_limited_activities_for_player(
            player, recency_limit)
            for player in players}

        activities_by_player_name = await async_utils.collect_map(tasks_by_player_name)

        return _find_shared_fireteams(activities_by_player_name, min_size=min_size)

    async def get_recency_limited_activities_for_player(
            self, player: MinimalPlayer, recency_limit: datetime) -> Sequence[Activity]:
        log.debug(f"Getting activities for player {player.name}...")
        return list(
            filter(
                lambda a: a.time_period.start > recency_limit,
                await self._data_retriever.get_activities_for_player(
                    player, min_start_date=recency_limit)))


def _find_shared_fireteams(activities_by_player_name: Mapping[str, Sequence[Activity]],
                           min_size: int = 2) -> Sequence[Fireteam]:
    name_to_instance_ids = {player_name: set(map(lambda x: x.instance_id, v)) for player_name, v in
                            activities_by_player_name.items()}

    all_activities = _flatten(activities_by_player_name.values())
    return _find_fireteams(name_to_instance_ids,
                           _activities_by_instance_id(all_activities),
                           min_size)


def _combine_activities(activities: Sequence[Activity]) -> Activity:
    first_activity = first(activities)
    time_period: TimePeriod = first_activity.time_period

    for activity in rest(activities):
        if (activity.instance_id != first_activity.instance_id
            or activity.director_activity_hash != first_activity.director_activity_hash
            or activity.primary_mode != first_activity.primary_mode
            or activity.modes != first_activity.modes):
            raise ValueError("Cannot combine non-matching activities")
        time_period = time_period.combine(activity.time_period)


    return Activity(
        instance_id=first_activity.instance_id,
        director_activity_hash=first_activity.director_activity_hash,
        primary_mode=first_activity.primary_mode,
        modes=first_activity.modes,
        time_period=time_period)


def _activities_by_instance_id(activities: Iterable[Activity]) -> Mapping[int, Activity]:
    def instance_id(a: Activity) -> int:
        return a.instance_id

    return {key: _combine_activities(list(group)) for key, group in itertools.groupby(sorted(activities, key=instance_id), key=instance_id)}



def _find_fireteams(name_to_instance_ids: Mapping[str, Set[int]],
                    activities_by_instance_id: Mapping[int, Activity], min_size: int = 2):
    fireteams: Dict[int, Fireteam] = dict()
    for one, two in itertools.combinations(name_to_instance_ids.keys(), 2):
        shared_ids = name_to_instance_ids[one].intersection(name_to_instance_ids[two])
        for instance_id in shared_ids:
            if instance_id not in fireteams:
                fireteams[instance_id] = Fireteam(activity=activities_by_instance_id[instance_id],
                                                  member_names={one, two})
            else:
                fireteams[instance_id].member_names.update({one, two})
    return list(f for f in fireteams.values() if len(f.member_names) >= min_size)


T = TypeVar('T')


def _flatten(nested_sequence: Iterable[Iterable[T]]) -> Iterable[T]:
    return itertools.chain.from_iterable(nested_sequence)
