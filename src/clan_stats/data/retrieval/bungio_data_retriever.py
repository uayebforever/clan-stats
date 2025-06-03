import asyncio
import itertools
import logging
from datetime import datetime
from pathlib import Path
from typing import Union, Sequence, Optional

from bungio import Client
from bungio.models import DestinyClan, RuntimeGroupMemberType, DestinyComponentType, BungieMembershipType, \
    GroupsForMemberFilter, GroupType, UserSearchPrefixRequest

from clan_stats.data._bungie_api.api_helpers import activity_history_to
from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data._bungie_api.bungie_type_adapters import player_from_group_member, player_from_user_membership_data, \
    activity_from_destiny_activity, activity_with_post
from clan_stats.data._bungie_api.bungie_types import GroupResponse, SearchResultOfGroupMember, DestinyProfileResponse, \
    UserMembershipData, GetGroupsForMemberResponse, DestinyActivityHistoryResults, DestinyHistoricalStatsPeriodGroup, \
    DestinyPostGameCarnageReportData, UserSearchResponse
from clan_stats.data._bungie_api.typed_wrapper import find_clan_group
from clan_stats.data.manifest import Manifest, SqliteManifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, MinimalPlayer, Character, Membership
from clan_stats.util.async_utils import retrieve_paged
from clan_stats.util.itertools import flatten
from clan_stats.util.stopwatch import Stopwatch
from clan_stats.util.time import require_tz_aware_datetime

logger = logging.getLogger(__name__)

_PAGE_SIZE = 50


class BungioDataRetriever(DataRetriever):

    def __init__(self, api_key: str):
        self._client = Client(
            bungie_client_id="",
            bungie_client_secret="",
            bungie_token=api_key,
        )

    async def get_player(self, player_id: int) -> Player:
        raw_data = await self._client.api.get_membership_data_by_id(player_id, BungieMembershipType.NONE)
        return player_from_user_membership_data(
            UserMembershipData.model_validate(
                raw_data))

    async def get_characters_for_player(self, minimal_player: MinimalPlayer) -> Sequence[Character]:
        characters = DestinyProfileResponse.model_validate(await self._client.api.get_profile(
            minimal_player.primary_membership.membership_id,
            minimal_player.primary_membership.membership_type,
            components=[DestinyComponentType.CHARACTERS]))
        return [
            Character(
                membership=Membership(membership_id=character.membershipId,
                                      membership_type=character.membershipType),
                character_id=character.characterId,
                character_type=character.classType,
                power_level=character.light,
                player=minimal_player)
            for character in characters.characters.data.values()]

    async def get_clan(self, clan_id: int) -> Clan:
        logging.info("Getting clan %s", clan_id)
        clan_group = GroupResponse.model_validate(await self._client.api.get_group(clan_id))
        members = SearchResultOfGroupMember.model_validate(
            await self._client.api.get_members_of_group(group_id=clan_id, currentpage=1))

        players = [player_from_group_member(m) for m in members.results]
        logging.debug("Clan %s (%s) has %s players", clan_id, clan_group.detail.name, len(players))
        return Clan(
            id=clan_group.detail.groupId,
            name=clan_group.detail.name,
            players=players,
            characters=flatten(await asyncio.gather(*[self.get_characters_for_player(p) for p in players])))

    async def get_clan_for_player(self, player: Player) -> Optional[Clan]:
        groups = GetGroupsForMemberResponse.model_validate(
            await self._client.api.get_groups_for_member(
                filter=GroupsForMemberFilter.ALL,
                group_type=GroupType.CLAN,
                membership_id=player.primary_membership.membership_id,
                membership_type=player.primary_membership.membership_type))

        clan_group = find_clan_group(groups.results)

        if clan_group is None:
            return None

        return await self.get_clan(clan_group.group.groupId)

    async def get_activities_for_player(self, player: MinimalPlayer, min_start_date: Optional[datetime] = None,
                                        mode: GameMode = GameMode.NONE) -> Sequence[Activity]:
        if min_start_date is not None:
            require_tz_aware_datetime(min_start_date)
        characters = await self.get_characters_for_player(player)

        raw_activities = flatten(await asyncio.gather(*[
            self._get_activity_history(
                player.primary_membership.membership_id,
                player.primary_membership.membership_type,
                c.character_id)
            for c in characters]))

        return [activity_from_destiny_activity(a) for a in raw_activities]

    async def get_post_for_activity(self, activity: Activity) -> ActivityWithPost:
        return activity_with_post(
            activity=activity,
            post=DestinyPostGameCarnageReportData.model_validate(
                await self._client.api.get_post_game_carnage_report(activity.instance_id)))

    async def find_players(self, identifier: Union[int, str]) -> Sequence[Player]:
        raise NotImplementedError
        # UserSearchPrefixRequest.
        # response = UserSearchResponse.model_validate(
        #     await self._client.api.search_by_global_name_post())

    async def get_manifest(self) -> Manifest:
        logger.debug("Retrieving Destiny Manifest")
        stopwatch = Stopwatch.started()
        target_dir = Path.cwd()
        target_filebase = "manifest"
        target_extension = "sqlite3"

        manifest_path = target_dir.joinpath(target_filebase + "." + target_extension)

        if not manifest_path.exists():
            raise RuntimeError("manifest not downloaded?!")

        logger.debug("Retrieved manifest to %s in %s", manifest_path, stopwatch.elapsed())
        return SqliteManifest(manifest_path)

    async def _get_activity_history(
            self,
            membership_id: int,
            membership_type,
            character_id: int,
            mode: int = 0,
            min_start_date: Optional[datetime] = None) -> Sequence[DestinyHistoricalStatsPeriodGroup]:
        async def _get_page(page_num: int) -> Sequence[DestinyHistoricalStatsPeriodGroup]:
            response = DestinyActivityHistoryResults.model_validate(
                await self._client.api.get_activity_history(
                    destiny_membership_id=membership_id,
                    membership_type=membership_type,
                    character_id=character_id,
                    mode=mode,
                    count=_PAGE_SIZE,
                    page=page_num,
                ))
            return response.activities

        return await retrieve_paged(_get_page, enough=activity_history_to(min_start_date))
