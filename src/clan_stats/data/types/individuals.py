from datetime import datetime
from typing import NamedTuple, Any, Optional, Dict, Mapping
from pydantic import BaseModel, Field

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType


class Membership(BaseModel):
    model_config = {"frozen": True}

    membership_id: int
    membership_type: MembershipType


class MinimalPlayer(BaseModel):
    primary_membership: Membership
    name: str

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, MinimalPlayer):
            return False
        return self.primary_membership == other.primary_membership

    def __lt__(self, other):
        if isinstance(other, MinimalPlayer):
            return self.name < other.name
        else:
            return False


class GroupMinimalPlayer(MinimalPlayer):
    last_online: datetime
    group_join_date: datetime


class MinimalPlayerWithClan(MinimalPlayer):
    clan_name: Optional[str] = Field(default=None)


class Player(MinimalPlayer):
    bungie_id: Optional[int]
    is_private: Optional[bool]
    all_names: Optional[Mapping[str, Optional[str]]]
    last_seen: Optional[datetime]

    def minimal_player(self) -> MinimalPlayer:
        return MinimalPlayer(primary_membership=self.primary_membership, name=self.name)


class Character(BaseModel):
    membership: Membership
    character_id: int
    character_type: CharacterType
    power_level: int
    player: MinimalPlayer
