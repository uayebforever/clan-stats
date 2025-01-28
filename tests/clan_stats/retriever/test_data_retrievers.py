from datetime import timedelta

import pytest

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType
from clan_stats.data.retrieval.aiobungie_rest_data_retriever import AioBungieRestDataRetriever
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.util.itertools import first


@pytest.fixture(params=[
    AioBungieRestDataRetriever
])
def retriever(request, bungie_api_key) -> DataRetriever:
    return request.param(api_key=bungie_api_key)


class TestDataRetrievers:

    @pytest.mark.asyncio
    async def test_get_player(self, retriever: DataRetriever):
        bungie_membership_id = 17970080

        async with retriever:
            player = await retriever.get_player(bungie_membership_id)

            assert player.name == "uayebforever#2982"
            assert player.primary_membership.membership_type == MembershipType.XBOX

            player_from_membership = await retriever.get_player(
                player.primary_membership.membership_id)

            assert player_from_membership.bungie_id == player.bungie_id

    @pytest.mark.asyncio
    async def test_get_characters_for_player(self, retriever: DataRetriever):
        bungie_membership_id = 17970080

        async with retriever:
            player = await retriever.get_player(bungie_membership_id)
            characters = await retriever.get_characters_for_player(player)

        assert len(characters) > 0
        a_character = first(characters)
        assert a_character.character_id > 0
        assert a_character.character_type != CharacterType.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_clan(self, retriever: DataRetriever):
        clan_id = 4402352

        async with retriever:
            clan = await retriever.get_clan(clan_id)

            assert clan.id == 4402352
            assert clan.name == "QUΔNTUM"
            assert len(clan.players) > 0



    @pytest.mark.asyncio
    async def test_get_clan_for_player(self, retriever: DataRetriever):

        bungie_membership_id = 17970080

        async with retriever:
            player = await retriever.get_player(bungie_membership_id)
            clan = await retriever.get_clan_for_player(player)

            assert clan.id == 4402352
            assert clan.name == "QUΔNTUM"
            assert len(clan.players) > 0
            assert player in clan.players

    @pytest.mark.asyncio
    async def test_get_activities_for_player(self, retriever: DataRetriever):
        bungie_membership_id = 17970080

        async with retriever:
            player = await retriever.get_player(bungie_membership_id)

            activities = await retriever.get_activities_for_player(player)

            assert len(activities) > 0

            an_activity = activities[0]

            assert an_activity.time_period.length > timedelta(seconds=1)
            assert an_activity.director_activity_hash > 0

    @pytest.mark.asyncio
    async def test_get_post_for_activity(self, retriever: DataRetriever):
        bungie_membership_id = 17970080

        async with retriever:
            player = await retriever.get_player(bungie_membership_id)
            activity = first(await retriever.get_activities_for_player(player))

            activity_with_post = await retriever.get_post_for_activity(activity)

            assert len(activity_with_post.players) > 0

            assert player.primary_membership in [p.primary_membership
                                                 for p in activity_with_post.players]
