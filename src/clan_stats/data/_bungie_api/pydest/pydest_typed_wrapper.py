from typing import Mapping, Any, Awaitable, Sequence, List, Optional

import pydest
from clan_stats.data._bungie_api.bungie_types import UserMembershipData, DestinyProfileResponse, \
    DestinyCharacterComponent, GetGroupsForMemberResponse, GroupMembership, DestinyActivityHistoryResults, \
    DestinyHistoricalStatsActivity, DestinyPostGameCarnageReportData, SearchResultOfGroupMember, GroupMember, \
    GroupResponse
from clan_stats.data._bungie_api.typed_wrapper import BungieRestApiTypedWrapper


class DestinyApiError(RuntimeError):
    pass


class PydestTypedWrapper(BungieRestApiTypedWrapper):

    def __init__(self, api_key: str) -> None:
        self.pydest: pydest.Pydest = pydest.Pydest(api_key)
        self.pydestapi: pydest.API = self.pydest.api

    async def get_membership_data_by_id(self, player_id: int) -> UserMembershipData:
        response = await _response_for(self.pydestapi.get_membership_data_by_id(player_id))
        return UserMembershipData(**response)

    async def get_profile_characters(self,
                                     membership_id: int,
                                     membership_type: int
                                     ) -> Mapping[int, DestinyCharacterComponent]:
        response = await _response_for(self.pydestapi.get_profile(
            membership_type, membership_id, ["Characters"]))
        profile = DestinyProfileResponse(**response)
        if profile.characters is None:
            raise ValueError("profile response without characters")
        return profile.characters.data

    async def get_group(self, group_id: int) -> GroupResponse:
        url = pydest.api.GROUP_URL + '{}/'
        url = url.format(group_id)
        response = await _response_for(self.pydestapi._get_request(url))
        return GroupResponse(**response)

    async def get_groups_for_member(self,
                                    membership_id: int,
                                    membership_type: int
                                    ) -> Sequence[GroupMembership]:
        response = await _response_for(self.pydestapi.get_groups_for_member(
            membership_type, membership_id))
        typed_response = GetGroupsForMemberResponse(**response)
        return typed_response.results

    async def get_activity_history(self, membership_id: int, membership_type: int, character_id: int,
                                   min_start_date: int = None) -> Sequence[DestinyHistoricalStatsActivity]:
        response = await _response_for(self.pydestapi.get_activity_history(
            membership_type, membership_id, character_id, count=min_start_date))
        typed_response = DestinyActivityHistoryResults(**response)
        return typed_response.activities

    async def get_post_game_carnage_report(self, activity_id: int) -> DestinyPostGameCarnageReportData:
        response = await _response_for(self.pydestapi.get_post_game_carnage_report(activity_id))
        return DestinyPostGameCarnageReportData(**response)

    # async def search(self):
    #     self.pydestapi.s

    async def get_members_of_group(self, group_id: int) -> Sequence[GroupMember]:
        response = await _response_for(self.pydestapi.get_members_of_group(group_id))
        typed_response = SearchResultOfGroupMember(**response)
        return typed_response.results


async def _response_for(awaitable: Awaitable[Mapping[str, Mapping[str, Any]]]) -> Mapping[str, Any]:
    data = await awaitable
    if data["ErrorCode"] != 1:
        raise Exception()

    return data["Response"]
