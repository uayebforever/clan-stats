import json
from datetime import datetime, timezone
from pathlib import Path
from typing import ContextManager, MutableMapping, Optional, Sequence, Iterator, Iterable

from clan_stats.data.types.activities import Activity
from clan_stats.data.types.individuals import Membership



class ActivityDatabase:

    def __init__(self, database: MutableMapping):
        self.db = database

    def update(self, activities: Iterable[Activity]):
        for activity in activities:
            try:
                self.get(activity.time_period.start)
            except KeyError:
                self.set(activity)

    def get(self, key: int|datetime|float) -> Activity:
        if isinstance(key, datetime):
            key = str(int(key.timestamp()))
        elif isinstance(key, float):
            key = str(int(key))
        elif isinstance(key, int):
            key = str(key)
        else:
            raise TypeError()
        raw = self.db[str(key)]
        return Activity(**json.loads(raw))

    def set(self, activity: Activity) -> None:
        key = str(int(activity.time_period.start.timestamp()))
        self.db[key] = json.dumps(activity.model_dump(mode="json"))

    def keys(self) -> Iterator[datetime]:
        for key in self.db:
            yield datetime.fromtimestamp(int(key), timezone.utc)