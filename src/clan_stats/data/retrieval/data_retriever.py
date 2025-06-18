import abc
from datetime import datetime
from types import TracebackType
from typing import List, Sequence, Mapping, Dict, Union, Optional, AsyncContextManager, Type

from .._bungie_api.bungie_enums import GameMode
from ..manifest import Manifest
from ..types.activities import ActivityWithPost, Activity
from ..types.clan import Clan, MinimalClan
from ..types.individuals import Player, Character, MinimalPlayer


class DataRetriever(AsyncContextManager, abc.ABC):


    async def __aexit__(self,
                        exception_type: Type[BaseException] | None,
                        exception: BaseException | None,
                        traceback: TracebackType | None) -> bool | None:
        pass

    @abc.abstractmethod
    async def get_player(self, player_id: int) -> Player:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_characters_for_player(self, minimal_player: MinimalPlayer) -> Sequence[Character]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_clan(self, clan_id: int) -> Clan:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_clan_for_player(self, player: Player) -> Optional[Clan]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_activities_for_player(self,
                                        player: MinimalPlayer,
                                        min_start_date: Optional[datetime] = None,
                                        mode: GameMode = GameMode.NONE
                                        ) -> Sequence[Activity]:
        raise NotImplementedError()

    async def get_activities_for_player_list(self,
                                             players: List[Player],
                                             mode: GameMode = GameMode.NONE) -> Mapping[Player, Sequence[Activity]]:
        result: Dict[Player, Sequence[Activity]] = dict()
        for player in players:
            result[player] = await self.get_activities_for_player(player, mode=mode)
        return result

    @abc.abstractmethod
    async def get_post_for_activity(self, activity: Activity) -> ActivityWithPost:
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_players(self, identifier: Union[int, str]) -> Sequence[Player]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def find_clans(self, identifier: Union[int, str]) -> Sequence[MinimalClan]:
        raise NotImplementedError()

    @abc.abstractmethod
    async def get_manifest(self) -> Manifest:
        raise NotImplementedError()