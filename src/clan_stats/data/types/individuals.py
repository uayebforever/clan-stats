from datetime import datetime
from enum import StrEnum, auto
from typing import NamedTuple, Any, Optional, Dict, Mapping
from pydantic import BaseModel, Field

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType, ClanMemberType


class Membership(BaseModel):
    model_config = {"frozen": True}

    membership_id: int
    membership_type: MembershipType


class CrossSaveStatus(StrEnum):
    PRIMARY = auto()
    OVERRIDDEN = auto()
    NONE = auto()

    def single_letter(self) -> str:
        if self is self.PRIMARY: return "P"
        if self is self.OVERRIDDEN: return "O"
        if self is self.NONE: return "N"
        raise TypeError(f"Unknown CrossSaveStatus {self}")

class DetailedMembership(Membership):
    platform_display_name: str
    cross_save_status: CrossSaveStatus


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
    group_membership_type: ClanMemberType


class MinimalPlayerWithClan(MinimalPlayer):
    clan_name: Optional[str] = Field(default=None)


class Player(MinimalPlayer):
    bungie_id: int
    is_private: Optional[bool]
    last_seen: Optional[datetime]
    all_memberships: Optional[Mapping[str, DetailedMembership]]

    def minimal_player(self) -> MinimalPlayer:
        return MinimalPlayer(primary_membership=self.primary_membership, name=self.name)


class Character(BaseModel):
    membership: Membership
    character_id: int
    character_type: CharacterType
    power_level: int
    player: MinimalPlayer


def last_seen(player: Player):
    return player.last_on_destiny
