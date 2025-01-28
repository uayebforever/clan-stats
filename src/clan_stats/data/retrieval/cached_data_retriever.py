import contextlib
import itertools
import json
from datetime import datetime, timezone, timedelta
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import Union, Sequence, Optional, Iterator, MutableMapping, NamedTuple, Generic, \
    TypeVar, Callable, Awaitable, Type, Mapping, Any
from logging import getLogger

from pydantic import BaseModel

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data._bungie_api.bungie_exceptions import PrivacyError
from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.actvity_database import ActivityDatabase
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.retrieval.databases import KeyValueDatabase
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, MinimalPlayer, Character, Membership
from clan_stats.util import time
from clan_stats.util.time import now

PLAYER_CACHE_LIFETIME = time.TP_1h
ACTIVITY_DATA_REFRESH_LIMIT_TIME = time.TP_1h
ACTIVITY_CACHE_LIFETIME = time.TP_1Y

_BaseModelT = TypeVar("_BaseModelT", bound=BaseModel)

logger = getLogger(__name__)


class CachedDataRetriever(DataRetriever):

    def __init__(self, delegate: DataRetriever, database_directory: Path):
        self._delegate = delegate
        self._database_directory = database_directory
        self._activity_cache_dates = None

    async def __aenter__(self):
        self._activity_cache_dates = self.database("activity_cache_dates")
        self._activity_cache_dates_db = self._activity_cache_dates.__enter__()
        return await self._delegate.__aenter__()

    async def __aexit__(self, exception_type: Type[BaseException] | None, exception: BaseException | None,
                        traceback: TracebackType | None) -> bool | None:
        self._activity_cache_dates.__exit__(exception_type, exception, traceback)
        return await self._delegate.__aexit__(exception_type, exception, traceback)

    @contextlib.contextmanager
    def database(self, name: str) -> Iterator['TimeStampedDataMappingWrapper']:
        if not self._database_directory.exists():
            self._database_directory.mkdir()
        db_path = self._database_directory.joinpath(name + ".gdbm").absolute()
        with KeyValueDatabase(db_path) as db:
            yield TimeStampedDataMappingWrapper(SerializedMapping(db))

    @contextlib.contextmanager
    def activity_database(self, membership: Membership) -> Iterator[ActivityDatabase]:
        if not self._database_directory.exists():
            self._database_directory.mkdir()
        filename = f"activities_{membership.membership_id}_{membership.membership_type}.gdbm"
        db_path = self._database_directory.joinpath(filename).absolute()
        with KeyValueDatabase(db_path) as db:
            yield ActivityDatabase(db)

    async def get_player(self, player_id: int) -> Player:
        with self.database("players") as db:
            return await _get_with_cache(db, player_id, PLAYER_CACHE_LIFETIME,
                                         Player,
                                         partial(self._delegate.get_player, player_id))

    async def get_characters_for_player(self, minimal_player: MinimalPlayer) -> Sequence[Character]:
        with self.database("player_characters") as db:
            return await _get_with_cache(
                db,
                minimal_player.primary_membership.membership_id,
                PLAYER_CACHE_LIFETIME,
                Character,
                partial(self._delegate.get_characters_for_player, minimal_player))

    async def get_clan_for_player(self, player: Player) -> Optional[Clan]:
        with self.database("player_clan") as db:
            return await _get_with_cache(
                db,
                player.primary_membership.membership_id,
                PLAYER_CACHE_LIFETIME,
                Clan,
                partial(self._delegate.get_clan_for_player, player))

    async def get_activities_for_player(
            self,
            player: MinimalPlayer,
            min_start_date: Optional[datetime] = None,
            mode: GameMode = GameMode.NONE
    ) -> Sequence[Activity]:
        if mode != GameMode.NONE:
            # Caching only set up for all activities
            return await self._delegate.get_activities_for_player(player, min_start_date, mode)

        with (self.activity_database(player.primary_membership) as db):
            cache_status = self._activity_cache_dates_db
            try:
                cache_date: TimeStampedData = cache_status[player.primary_membership.membership_id]
            except KeyError:
                logger.info("No cached activities for player %s", player.name)
                cache_date = TimeStampedData(
                    timestamp=datetime.fromtimestamp(0, timezone.utc),
                    data=datetime.fromtimestamp(0, timezone.utc))

            activity_dates = list(db.keys())

            if (self._need_recent_data(cache_date, activity_dates, min_start_date)
                    or self._need_older_data(cache_date, activity_dates, min_start_date)):
                if not self._need_older_data(cache_date, activity_dates, min_start_date):
                    logger.info("Stale cache, getting recent activities for player %s", player.name)
                    new_data = await self._delegate.get_activities_for_player(
                        player,
                        min_start_date=cache_date.timestamp)
                    db.update(new_data)
                    if len(new_data) == 0:
                        cache_start_date = now().timestamp()
                    else:
                        cache_start_date = min(
                            (a.time_period.start.timestamp() for a in new_data))
                    cache_status[player.primary_membership.membership_id] = cache_start_date
                else:
                    logger.info("Stale chache, getting full activities for player %s", player.name)
                    # Need whole data set
                    try:
                        new_data = await self._delegate.get_activities_for_player(
                            player,
                            min_start_date=min_start_date)
                    except PrivacyError:
                        cache_status[player.primary_membership.membership_id] = None
                        return []

                    db.update(new_data)
                    if len(new_data) == 0:
                        cache_start_date = now().timestamp()
                    else:
                        cache_start_date = min(
                            (a.time_period.start.timestamp() for a in new_data))
                    cache_status[player.primary_membership.membership_id] = cache_start_date
                    return new_data

            if min_start_date is None:
                return [db.get(k) for k in sorted(db.keys())]
            else:
                return [db.get(k)
                        for k in
                        filter(lambda d: d > min_start_date, sorted(db.keys()))]

    def _need_recent_data(self,
                          cache_date: 'TimeStampedData',
                          activity_dates: Sequence[datetime],
                          min_start_date: Optional[datetime]) -> bool:
        return (cache_date.data is not None
                and (len(activity_dates) == 0
                     or _expired(cache_date.timestamp, ACTIVITY_DATA_REFRESH_LIMIT_TIME)))

    def _need_older_data(self,
                         cache_date: 'TimeStampedData',
                         activity_dates: Sequence[datetime],
                         min_start_date: Optional[datetime]) -> bool:
        return (
                cache_date.data is not None
                and (len(activity_dates) == 0
                     or (min_start_date is not None and min(activity_dates) > min_start_date)))

    async def get_post_for_activity(self, activity: Activity) -> ActivityWithPost:
        with self.database("post_activities") as db:
            return await _get_with_cache(
                db,
                activity.instance_id,
                ACTIVITY_CACHE_LIFETIME,
                ActivityWithPost,
                partial(self._delegate.get_post_for_activity, activity))

    async def find_players(self, identifier: Union[int, str]) -> Sequence[Player]:
        return await self._delegate.find_players(identifier)

    async def get_manifest(self) -> Manifest:
        return await self._delegate.get_manifest()

    async def get_clan(self, clan_id: int) -> Clan:
        with self.database("clans") as db:
            return await _get_with_cache(
                db,
                clan_id,
                PLAYER_CACHE_LIFETIME,
                Clan,
                partial(self._delegate.get_clan, clan_id))


_T = TypeVar('_T')
_K = TypeVar('_K')
_V = TypeVar('_V')
_K_str_int = TypeVar('_K_str_int', str, int)


class TimeStampedData(NamedTuple, Generic[_T]):
    timestamp: datetime
    data: _T


class SerializedMapping(MutableMapping, Generic[_K_str_int, _V]):

    def __init__(self, delegate: MutableMapping):
        self.delegate: MutableMapping[str, str] = delegate

    def __getitem__(self, key: _K_str_int) -> _V:
        key = self._mangle_key(key)
        raw = self.delegate.__getitem__(key)
        decoded = json.loads(raw)
        return decoded

    def __setitem__(self, key: _K_str_int, data: _V):
        key = self._mangle_key(key)
        self.delegate[key] = json.dumps(data)

    def __delitem__(self, key: _K_str_int):
        return self.delegate.__delitem__(key)

    def __len__(self):
        return self.delegate.__len__()

    def __iter__(self) -> Iterator[_V]:
        return self.delegate.__iter__()

    def _mangle_key(self, key: Union[int, str]) -> str:
        if isinstance(key, int):
            return str(key)
        elif isinstance(key, str):
            return key
        else:
            raise KeyError("Key must be int or str")


class TimeStampedDataMappingWrapper(MutableMapping, Generic[_T]):

    def __init__(self, delegate: MutableMapping):
        self.delegate = delegate

    def __getitem__(self, key) -> TimeStampedData[_T]:
        decoded = self.delegate.__getitem__(key)
        return TimeStampedData(
            timestamp=datetime.fromtimestamp(decoded["timestamp"], timezone.utc),
            data=decoded["data"])

    def __setitem__(self, key, data: _T):
        if isinstance(data, TimeStampedData):
            self.delegate[key] = {"timestamp": data.timestamp.timestamp(),
                                  "data": data.data}
        else:
            self.delegate[key] = {"timestamp": time.now().timestamp(),
                                  "data": data}

    def __delitem__(self, key):
        return self.delegate.__delitem__(key)

    def __len__(self):
        return self.delegate.__len__()

    def __iter__(self) -> Iterator[TimeStampedData[_T]]:
        return self.delegate.__iter__()


def _store_return(db: MutableMapping, key: Union[str, int], data: _T) -> _T:
    db[key] = data
    return data


def _expired(timestamp: datetime, lifetime: timedelta):
    return time.now() - timestamp > lifetime


async def _get_with_cache(cache: TimeStampedDataMappingWrapper[_T],
                          key: _K_str_int,
                          lifetime: timedelta,
                          pydantic_type: Type[_BaseModelT],
                          supplier: Callable[[], Awaitable[_BaseModelT]]):
    try:
        data = cache[key]
    except KeyError:
        logger.debug("No cache value for %s", key)
        value = await supplier()
        cache[key] = _pydantic_to_python(value)
        return value

    if _expired(data.timestamp, lifetime):
        logger.debug("Expired cache value for %s", key)
        value = await supplier()
        cache[key] = _pydantic_to_python(value)
        return value
    return _python_to_pydantic(data.data, pydantic_type)


def _pydantic_to_python(pydantic_object: BaseModel | Sequence[BaseModel]
                        ) -> Mapping[str, Any] | Sequence[Mapping[str, Any]]:
    if isinstance(pydantic_object, Sequence):
        return [i.model_dump(mode="json") for i in pydantic_object]
    elif isinstance(pydantic_object, BaseModel):
        return pydantic_object.model_dump(mode="json")
    else:
        raise TypeError(f"Unexpected type {type(pydantic_object)}")


def _python_to_pydantic(obj: Any, pydantic_type: Type[_BaseModelT]
                        ) -> _BaseModelT | Sequence[_BaseModelT]:
    if isinstance(obj, Sequence):
        return [pydantic_type(**i) for i in obj]
    else:
        return pydantic_type(**obj)
