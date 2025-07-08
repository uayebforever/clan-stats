import logging
from pydantic import Field
from datetime import datetime, timedelta
from typing import Sequence, Iterable, TypeVar, Optional

from pydantic import BaseModel, ConfigDict

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.types.individuals import MinimalPlayerWithClan
from clan_stats.util.time import TimePeriod

logger = logging.getLogger(__name__)


class Activity(BaseModel):
    model_config = ConfigDict(frozen=True)
    
    instance_id: int
    director_activity_hash: int
    time_period: TimePeriod
    primary_mode: GameMode
    modes: Sequence[GameMode]
    completed: Optional[bool] = Field(default=None)

    @staticmethod
    def start_time(activity: 'Activity') -> datetime:
        return activity.time_period.start

    @staticmethod
    def end_time(activity: 'Activity') -> datetime:
        return activity.time_period.end

    @staticmethod
    def length(activity: 'Activity') -> timedelta:
        return activity.time_period.length


class ActivityWithPost(Activity):
    players: Sequence[MinimalPlayerWithClan]

class ActivityInstance(BaseModel):
    """This represents an activity instance, which potentially has multiple players in it.
    
    The design of the Destiny API is such that we can only infer the contents of this object by making
    requests for a players activities and post game carnage reports. Therefore, these objects are often 
    incomplete, and so we must track what we know vs what we could query for.

    """
    model_config = ConfigDict(frozen=True)

    player_activity_data: Sequence[Activity]
    post_game_carnage_report: Optional[]



_T_Activity = TypeVar('_T_Activity', bound=Activity)


def filter_activities_by_date(activities: Optional[Sequence[_T_Activity]],
                              start: datetime
                              ) -> Optional[Sequence[_T_Activity]]:
    if activities is None:
        return None
    return [a
            for a in activities
            if a.time_period.start > start]
