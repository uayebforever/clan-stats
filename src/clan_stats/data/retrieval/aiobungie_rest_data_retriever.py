import itertools
import logging
from datetime import datetime
from pathlib import Path
from types import TracebackType
from typing import Union, Sequence, Optional, Type

import aiobungie.error
from clan_stats.data._bungie_api.aiobungie.aiobungie_typed_wrapper import AioBungieTypedWrapper
from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data._bungie_api.bungie_exceptions import PrivacyError
from clan_stats.data._bungie_api.bungie_type_adapters import player_from_user_membership_data, player_from_group_member, \
    activity_from_destiny_activity, activity_with_post, primary_membership_from_cards
from clan_stats.data._bungie_api.typed_wrapper import find_clan_group
from clan_stats.data.manifest import Manifest, SqliteManifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import ActivityWithPost, Activity
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, Character, MinimalPlayer, Membership
from clan_stats.util.async_utils import collect_results
from clan_stats.util.itertools import flatten
from clan_stats.util.stopwatch import Stopwatch
from clan_stats.util.time import require_tz_aware_datetime

logger = logging.getLogger(__name__)


class AioBungieRestDataRetriever(DataRetriever):

    def __init__(self, api_key: str) -> None:
        self._wrapper = AioBungieTypedWrapper(api_key)

    async def __aenter__(self):
        return await self._wrapper.__aenter__()

    async def __aexit__(self, exception_type: Type[BaseException] | None, exception: BaseException | None,
                        traceback: TracebackType | None) -> bool | None:
        return await self._wrapper.__aexit__(exception_type, exception, traceback)

    async def get_player(self, player_id: int) -> Player:
        user_data = await self._wrapper.get_membership_data_by_id(player_id)
        player = player_from_user_membership_data(user_data)
        return player

    async def get_characters_for_player(self, player: MinimalPlayer) -> Sequence[Character]:
        try:
            characters = await self._wrapper.get_profile_characters(
                player.primary_membership.membership_id,
                player.primary_membership.membership_type)
        except aiobungie.error.InternalServerError as e:
            logger.warning("InternalServerError '%s: %s' while retrieving characters for %s",
                           e.error_status,
                           e.message,
                           player.name)
            characters = {}

        return [
            Character(
                membership=Membership(membership_id=character.membershipId,
                                      membership_type=character.membershipType),
                character_id=character.characterId,
                character_type=character.classType,
                power_level=character.light,
                player=player)
            for character in characters.values()]

    async def get_clan(self, clan_id: int) -> Clan:
        logger.debug("Getting clan %s", clan_id)
        clan_group = await self._wrapper.get_group(clan_id)
        group_members = await self._wrapper.get_members_of_group(group_id=clan_id)

        players = [player_from_group_member(m) for m in group_members]
        return Clan(
            id=clan_group.detail.groupId,
            name=clan_group.detail.name,
            players=players,
            characters=flatten(await collect_results([self.get_characters_for_player(p) for p in players])))

    async def get_clan_for_player(self, player: Player) -> Optional[Clan]:
        groups = await self._wrapper.get_groups_for_member(
            player.primary_membership.membership_id,
            player.primary_membership.membership_type)

        clan_group = find_clan_group(groups)

        if clan_group is None:
            return None

        logger.debug("Getting player %s clan %s", player.name, clan_group.group.groupId)

        group_members = await self._wrapper.get_members_of_group(clan_group.group.groupId)

        players = [player_from_group_member(m) for m in group_members]
        return Clan(
            id=clan_group.group.groupId,
            name=clan_group.group.name,
            players=players,
            characters=list(itertools.chain(*[
                await self.get_characters_for_player(p) for p in players])))

    async def get_activities_for_player(
            self,
            player: MinimalPlayer,
            min_start_date: Optional[datetime] = None,
            mode: GameMode = GameMode.NONE,
    ) -> Optional[Sequence[Activity]]:
        if min_start_date is not None:
            require_tz_aware_datetime(min_start_date)
        characters = await self.get_characters_for_player(player)

        activities = []
        for character in characters:
            try:
                raw_activities = await self._wrapper.get_activity_history(
                    membership_id=player.primary_membership.membership_id,
                    membership_type=player.primary_membership.membership_type,
                    character_id=character.character_id,
                    min_start_date=min_start_date,
                    mode=mode
                )
            except PrivacyError:
                logger.warning("PrivacyError while attempting to retrieve activities for %s", player.name)
                return None
            activities.extend(
                [activity_from_destiny_activity(g) for g in raw_activities])

        return activities

    async def get_post_for_activity(self, activity: Activity) -> ActivityWithPost:
        post = await self._wrapper.get_post_game_carnage_report(activity.instance_id)
        return activity_with_post(activity, post)

    async def find_players(self, identifier: Union[int, str]) -> Sequence[Player]:
        results = await self._wrapper.search_users(str(identifier))
        players = []
        for result in results:
            players.append(Player(
                bungie_id=result.bungieNetMembershipId,
                name=result.combined_global_display_name(),
                is_private=False,
                last_seen=None,
                primary_membership=
                    primary_membership_from_cards(result.destinyMemberships),
                all_names={c.membershipType.name: c.displayName for c in result.destinyMemberships}
            ))
        return players

    async def get_manifest(self) -> Manifest:
        logger.debug("Retrieving Destiny Manifest")
        stopwatch = Stopwatch.started()
        target_dir = Path.cwd()
        target_filebase = "manifest"
        target_extension = "sqlite3"

        manifest_path = target_dir.joinpath(target_filebase + "." + target_extension)

        if not manifest_path.exists():
            logger.debug(f"Downloading manifest from Bungie to {target_dir}/{target_filebase}.{target_extension}")
            if manifest_path != await self._wrapper._client.download_sqlite_manifest(path=target_dir,
                                                                                     name=target_filebase):
                raise RuntimeError("Downloaded to wrong path")
        if not manifest_path.exists():
            raise RuntimeError("manifest not downloaded?!")

        logger.debug("Retrieved manifest to %s in %s", manifest_path, stopwatch.elapsed())
        return SqliteManifest(manifest_path)
