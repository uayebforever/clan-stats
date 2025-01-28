from datetime import datetime
from types import TracebackType
from typing import Sequence, Mapping, Type, Callable, Optional
from logging import getLogger

import aiobungie
from clan_stats.data._bungie_api.bungie_exceptions import PrivacyError
from clan_stats.data._bungie_api.bungie_types import UserMembershipData, GroupMember, DestinyPostGameCarnageReportData, \
    GroupMembership, DestinyCharacterComponent, DestinyProfileResponse, \
    GetGroupsForMemberResponse, DestinyActivityHistoryResults, SearchResultOfGroupMember, \
    DestinyHistoricalStatsPeriodGroup, GroupResponse, UserSearchResponse, UserSearchResponseDetail
from clan_stats.data._bungie_api.typed_wrapper import BungieRestApiTypedWrapper
from clan_stats.util.async_utils import retrieve_paged
from clan_stats.util.itertools import first

log = getLogger(__name__)

PAGE_SIZE = 50


class AioBungieTypedWrapper(BungieRestApiTypedWrapper):

    def __init__(self, api_key: str):
        self._client = aiobungie.RESTClient(api_key)

    async def __aenter__(self):
        await self._client.__aenter__()

    async def __aexit__(self,
                        exc_type: Type[BaseException] | None,
                        exc_val: BaseException | None,
                        exc_tb: TracebackType | None) -> bool | None:
        return await self._client.__aexit__(exc_tb, exc_val, exc_tb)

    async def get_membership_data_by_id(self, player_id: int) -> UserMembershipData:
        raw_user = await self._client.fetch_membership_from_id(player_id)
        return UserMembershipData(**raw_user)

    async def get_profile_characters(self, membership_id: int, membership_type: int) -> Mapping[
        int, DestinyCharacterComponent]:
        raw_profile = await self._client.fetch_profile(membership_id,
                                                       membership_type,
                                                       [aiobungie.ComponentType.CHARACTERS])
        profile = DestinyProfileResponse(**raw_profile)
        if profile.characters is None:
            raise ValueError("profile response without characters")
        return profile.characters.data

    async def get_group(self, group_id: int) -> GroupResponse:
        response = await self._client.fetch_clan_from_id(group_id)
        typed_response = GroupResponse(**response)
        return typed_response

    async def get_groups_for_member(self, membership_id: int, membership_type: int) -> Sequence[GroupMembership]:
        response = await self._client.fetch_groups_for_member(membership_id, membership_type)
        typed_response = GetGroupsForMemberResponse(**response)
        return typed_response.results

    async def search_users(self, search_string: str) -> Sequence[UserSearchResponseDetail]:
        response = await self._client.search_users(search_string)
        typed_response = UserSearchResponse(**response)
        log.debug(typed_response)
        return typed_response.searchResults


    async def get_activity_history(self,
                                   membership_id: int,
                                   membership_type: int,
                                   character_id: int,
                                   min_start_date: datetime = None,
                                   mode: int = 0
                                   ) -> Sequence[DestinyHistoricalStatsPeriodGroup]:
        async def _get_page(page_num: int) -> Sequence[DestinyHistoricalStatsPeriodGroup]:
            try:
                response = await self._client.fetch_activities(membership_id, character_id,
                                                               mode=mode,
                                                               membership_type=membership_type,
                                                               page=page_num,
                                                               limit=PAGE_SIZE)
            except aiobungie.error.InternalServerError as err:
                if err.message.startswith("The user has chosen for this data to be private"):
                    raise PrivacyError(
                        message=err.message,
                        membership_id=membership_id,
                        membership_type=membership_type,
                        original_exception=err)

            if "activities" not in response:
                return []

            typed_response = DestinyActivityHistoryResults(**response)
            return typed_response.activities

        return await retrieve_paged(_get_page, enough=_activity_history_to(min_start_date))

    async def get_post_game_carnage_report(self, activity_id: int) -> DestinyPostGameCarnageReportData:
        response = await self._client.fetch_post_activity(activity_id)
        return DestinyPostGameCarnageReportData(**response)

    async def get_members_of_group(self, group_id: int) -> Sequence[GroupMember]:
        response = await self._client.fetch_clan_members(group_id)
        typed_response = SearchResultOfGroupMember(**response)
        return typed_response.results


def _activity_history_to(start_date: Optional[datetime]) -> Optional[Callable[[list], bool]]:
    if start_date is None:
        return None

    def enough(activities: Sequence[DestinyHistoricalStatsPeriodGroup]) -> bool:
        return _time_of_oldest_activity(activities) < start_date

    return enough


def _time_of_oldest_activity(activities: Sequence[DestinyHistoricalStatsPeriodGroup]) -> datetime:
    return first(sorted(activities, key=_activity_time)).period


def _activity_time(activity: DestinyHistoricalStatsPeriodGroup) -> datetime:
    return activity.period
