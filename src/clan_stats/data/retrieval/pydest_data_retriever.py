import asyncio
from datetime import datetime
from typing import Union, Sequence, Optional, Any, Dict

from clan_stats.data._bungie_api.bungie_type_adapters import player_from_user_membership_data
from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data._bungie_api.pydest.pydest_typed_wrapper import PydestTypedWrapper
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, MinimalPlayer


class PyDestDataRetriever(DataRetriever):

    def __init__(self, api_key: str) -> None:
        self.pydest = PydestTypedWrapper(api_key)

    def get_activities_for_player(
            self,
            player: MinimalPlayer,
            min_start_date: Optional[datetime] = None
    ) -> Sequence[Activity]:
        raise NotImplementedError

    def get_post_for_activity(self, activity: Activity) -> ActivityWithPost:
        raise NotImplementedError

    def get_player(self, player_id: int) -> Player:
        return asyncio.run(self._async_get_player(player_id))

    async def _async_get_player(self, player_id: int) -> Player:
        user_data = await self.pydest.get_membership_data_by_id(player_id)
        player = player_from_user_membership_data(user_data)
        player.member_type = membership_type_from_membership_data(user_data)
        return player

    def find_players(self, identifier: Union[int, str]) -> Sequence[Player]:
        pass

    def get_clan_for_player(self, player: Player) -> Clan:
        groups = self._get_groups_for_player(player)

    def get_manifest(self) -> Manifest:
        pass

    def fetch_clan(self, clan_id: int) -> Clan:
        pass

    def _get_groups_for_player(self, player):
        pass

    async def _get_groups_for_members(self, membership_id: int) -> Dict[str, Any]:
        json = await self.pydest.api.get_groups_for_member()