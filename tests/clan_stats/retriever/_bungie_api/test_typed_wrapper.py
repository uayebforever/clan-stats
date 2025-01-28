from datetime import datetime, timezone
from typing import Callable, Type

import pytest

from clan_stats.data._bungie_api.aiobungie.aiobungie_typed_wrapper import AioBungieTypedWrapper
from clan_stats.data._bungie_api.bungie_exceptions import PrivacyError
# from clan_stats.data._bungie_api.pydest.pydest_typed_wrapper import PydestTypedWrapper
from clan_stats.data._bungie_api.typed_wrapper import BungieRestApiTypedWrapper, find_clan_group
from clan_stats.util.itertools import only


@pytest.fixture(params=[
    # PydestTypedWrapper,
    AioBungieTypedWrapper
])
def wrapper(request, bungie_api_key) -> BungieRestApiTypedWrapper:
    return request.param(bungie_api_key)


class TestPydestTypedWrapper:

    @pytest.mark.asyncio
    async def test_get_membership_data_by_id(self, wrapper):

        async with wrapper:
            user = await wrapper.get_membership_data_by_id(17970080)

        # assert user == ""

        assert user.bungieNetUser.membershipId == 17970080
        assert user.bungieNetUser.uniqueName == "uayebforever#2982"
        assert user.bungieNetUser.xboxDisplayName == "uayebforever"
        assert user.bungieNetUser.twitchDisplayName == "uayebforever"
        assert user.bungieNetUser.psnDisplayName is None

        assert len(user.destinyMemberships) > 0
        assert user.destinyMemberships[0].membershipId > 0
        assert user.destinyMemberships[0].membershipType > 0
        assert user.destinyMemberships[0].displayName == "uayebforever"

    @pytest.mark.asyncio
    async def test_get_profile_character(self,wrapper):
        membership_id = 4611686018469899232
        membership_type = 1

        async with wrapper:
            character_map = await wrapper.get_profile_characters(membership_id, membership_type)

        assert len(character_map) > 0

        characters = list(character_map.values())

        assert characters[0].membershipId == membership_id
        assert characters[0].membershipType == membership_type
        assert characters[0].characterId != 0

    @pytest.mark.asyncio
    async def test_get_group(self, wrapper):
        group_id = 4402352

        async with wrapper:
            clan_group = await wrapper.get_group(group_id)

        assert clan_group is not None

        assert clan_group.detail.name == "QUΔNTUM"
        assert clan_group.detail.groupId == group_id

    @pytest.mark.asyncio
    async def test_get_groups_for_member(self, wrapper):
        membership_id = 4611686018469899232
        membership_type = 1

        async with wrapper:
            groups = await wrapper.get_groups_for_member(membership_id, membership_type)

        assert len(groups) > 0

        clan_group = find_clan_group(groups)

        assert clan_group is not None

        assert clan_group.member.destinyUserInfo.membershipId == membership_id
        assert clan_group.member.destinyUserInfo.membershipType == membership_type

        assert clan_group.group.name == "QUΔNTUM"
        assert clan_group.group.groupId == 4402352

    @pytest.mark.asyncio
    async def test_get_activity_history(self, wrapper):
        membership_id = 4611686018469899232
        membership_type = 1
        character_id = 2305843009483904827

        async with wrapper:
            activities = await wrapper.get_activity_history(membership_id, membership_type, character_id,
                                                            min_start_date=10)

            assert len(activities) > 0

            activity = activities[0]

            assert activity.activityDetails.directorActivityHash != 0
            assert activity.period < datetime.now(timezone.utc)

            assert activity.values["timePlayedSeconds"].basic.value > 0

            for activity in activities:
                await wrapper.get_post_game_carnage_report(activity.activityDetails.instanceId)


    @pytest.mark.asyncio
    async def test_get_activity_history_private(self, wrapper):
        membership_id = 4611686018448321585
        membership_type = 1
        character_id = 2305843009267030653

        with pytest.raises(PrivacyError):
            async with wrapper:
                # player = await wrapper.get_membership_data_by_id(membership_id)
                activities = await wrapper.get_activity_history(membership_id, membership_type, character_id,
                                                                min_start_date=10)


    @pytest.mark.asyncio
    async def test_get_post_game_carnage_report(self, wrapper_factory: Callable[[], BungieRestApiTypedWrapper]):
        wrapper = wrapper_factory()
        activity_id = 14797661225

        async with wrapper:
            report = await wrapper.get_post_game_carnage_report(activity_id)

        assert report.activityDetails.directorActivityHash == 4179289725
        assert report.activityDetails.instanceId == 14797661225
        assert report.activityDetails.mode == 4
        assert report.activityDetails.modes == [7, 4]

        # assert report.period. == datetime(2024, 5, 15,
        #                                  1, 49, 27,
        #                                  tzinfo=TzInfo())

        assert len(report.entries) > 0

        assert report.entries[0].player.destinyUserInfo.membershipId == 4611686018467471522
        assert report.entries[0].player.destinyUserInfo.membershipType == 3

    @pytest.mark.asyncio
    async def test_get_members_of_group(self, wrapper_factory: Callable[[], BungieRestApiTypedWrapper]):
        wrapper = wrapper_factory()
        group_id = 4402352

        async with wrapper:
            members = await wrapper.get_members_of_group(group_id)

        assert len(members) > 0

        for member in members:
            assert member.groupId == group_id

    @pytest.mark.asyncio
    async def test_group_last_seen(self, wrapper_factory: Callable[[], BungieRestApiTypedWrapper]):
        wrapper = wrapper_factory()
        membership_id = 4611686018469899232
        membership_type = 1

        async with wrapper:
            user = await wrapper.get_membership_data_by_id(membership_id)
            groups = await wrapper.get_groups_for_member(membership_id, membership_type)
            assert len(groups) > 0
            clan_group = find_clan_group(groups)

            group = await wrapper.get_members_of_group(clan_group.group.groupId)

        group_member = only([gm for gm in group if gm.destinyUserInfo.membershipId == membership_id])

        assert datetime.fromtimestamp(group_member.lastOnlineStatusChange, timezone.utc) == user.bungieNetUser.lastUpdate

