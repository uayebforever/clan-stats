from dataclasses import dataclass, field
from datetime import datetime
from typing import Set

from clan_stats.data.types.activities import Activity


@dataclass
class Fireteam:
    activity: Activity
    member_names: Set[str] = field(default_factory=set)

    def activity_start(self) -> datetime:
        return self.activity.time_period.start

    def activity_end(self) -> datetime:
        return self.activity.time_period.end
