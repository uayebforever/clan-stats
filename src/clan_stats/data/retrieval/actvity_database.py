import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import ContextManager, MutableMapping, Optional, Sequence, Iterator, Iterable, Collection

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.types.activities import Activity
from clan_stats.data.types.individuals import Membership, MinimalPlayer
from clan_stats.util.time import TimePeriod


class SimpleActivityDatabase:

    def __init__(self, database: MutableMapping[str, str]):
        self.db = database

    def update(self, activities: Iterable[Activity]):
        for activity in activities:
            try:
                self.get(activity.time_period.start)
            except KeyError:
                self.set(activity)

    def get(self, key: int|datetime|float) -> Activity:
        if isinstance(key, datetime):
            db_key = str(int(key.timestamp()))
        elif isinstance(key, float):
            db_key = str(int(key))
        elif isinstance(key, int):
            db_key = str(key)
        else:
            raise TypeError()
        raw = self.db[db_key]
        return Activity(**json.loads(raw))

    def set(self, activity: Activity) -> None:
        key = str(int(activity.time_period.start.timestamp()))
        self.db[key] = json.dumps(activity.model_dump(mode="json"))

    def keys(self) -> Iterator[datetime]:
        for key in self.db:
            yield datetime.fromtimestamp(int(key), timezone.utc)

class ActivityDatabase(ABC):

    @abstractmethod
    def get_by_instance(self, player: MinimalPlayer, instance_id: int) -> Activity:
        raise NotImplementedError()

    @abstractmethod
    def get_in_period(self, player: MinimalPlayer, time_period: TimePeriod, game_mode: GameMode ) -> Sequence[Activity]:
        raise NotImplementedError()
