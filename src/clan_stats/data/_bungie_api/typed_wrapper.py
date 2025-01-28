from abc import ABCMeta, abstractmethod
from datetime import datetime
from types import TracebackType
from typing import Mapping, Sequence, AsyncContextManager, Type, List, Optional

from clan_stats.data._bungie_api.bungie_types import UserMembershipData, DestinyCharacterComponent, GroupMembership, \
    DestinyHistoricalStatsActivity, DestinyPostGameCarnageReportData, GroupMember, DestinyHistoricalStatsPeriodGroup, \
    GroupResponse


class BungieRestApiTypedWrapper(AsyncContextManager, metaclass=ABCMeta):


    async def __aexit__(self,
                        exception_type: Type[BaseException] | None,
                        exception: BaseException | None,
                        traceback: TracebackType | None) -> bool | None:
        pass

    @abstractmethod
    async def get_membership_data_by_id(self, player_id: int) -> UserMembershipData:
        pass

    @abstractmethod
    async def get_profile_characters(self,
                                     membership_id: int,
                                     membership_type: int
                                     ) -> Mapping[int, DestinyCharacterComponent]:
        pass

    @abstractmethod
    async def get_group(self, group_id: int) -> GroupResponse:
        pass

    @abstractmethod
    async def get_groups_for_member(self,
                                    membership_id: int,
                                    membership_type: int
                                    ) -> Sequence[GroupMembership]:
        pass

    @abstractmethod
    async def get_activity_history(self,
                                   membership_id: int,
                                   membership_type: int,
                                   character_id: int,
                                   min_start_date: Optional[datetime] = None,
                                   mode: int = 0
                                   ) -> Sequence[DestinyHistoricalStatsPeriodGroup]:
        pass

    @abstractmethod
    async def get_post_game_carnage_report(self,
                                           activity_id: int
                                           ) -> DestinyPostGameCarnageReportData:
        pass

    @abstractmethod
    async def get_members_of_group(self, group_id: int) -> Sequence[GroupMember]:
        pass


def find_clan_group(groups: Sequence[GroupMembership]) -> Optional[GroupMembership]:
    clan_type_groups: List[GroupMembership] = []
    for group in groups:
        if group.group.groupType == 1:
            clan_type_groups.append(group)
    if len(clan_type_groups) > 1:
        raise ValueError("More than one clan group in groups")
    if len(clan_type_groups) == 1:
        return clan_type_groups[0]
    return None
