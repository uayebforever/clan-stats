from datetime import datetime
from typing import Optional, Sequence, Mapping, Any, TypeVar

from pydantic import BaseModel, Field, ConfigDict
from pydantic import BaseModel, Field, ConfigDict, AliasGenerator, AliasChoices, BeforeValidator
from pydantic_core import PydanticUseDefault

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType, GameMode
from clan_stats.util.casing import to_snake_case

_AdaptableType = TypeVar('_AdaptableType', bound='UpstreamAdapter')


def display_name_from_name_and_code(name: str, code: int) -> str:
    return f"{name}#{code:04d}"


validation_aliases = AliasGenerator(
    validation_alias=lambda field_name: AliasChoices(field_name, to_snake_case(field_name))
)
class GeneralUser(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    membershipId: int
    uniqueName: str
    displayName: str

    lastUpdate: Optional[datetime] = Field(default=None)
    normalizedName: Optional[str] = Field(default=None)

    blizzardDisplayName: Optional[str] = Field(default=None)
    egsDisplayName: Optional[str] = Field(default=None)
    fbDisplayName: Optional[str] = Field(default=None)
    psnDisplayName: Optional[str] = Field(default=None)
    stadiaDisplayName: Optional[str] = Field(default=None)
    steamDisplayName: Optional[str] = Field(default=None)
    twitchDisplayName: Optional[str] = Field(default=None)
    xboxDisplayName: Optional[str] = Field(default=None)


class UserInfoCard(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    membershipType: MembershipType
    membershipId: int
    displayName: str
    # applicableMembershipTypes: Optional[Sequence[int]] = Field(default_factory=list)
    applicableMembershipTypes: Any = Field(default_factory=list)


class UserMembershipData(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    bungieNetUser: GeneralUser
    destinyMemberships: Sequence[UserInfoCard]

    primaryMembershipId: Optional[int] = Field(default=None)


class DestinyPlayer(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    destinyUserInfo: UserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    clanName: Optional[str] = Field(default=None)

    def best_name(self) -> str:
        if self.bungieNetUserInfo is not None:
            return self.bungieNetUserInfo.displayName
        return self.destinyUserInfo.displayName


class DestinyCharacterComponent(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    membershipId: int  # Convenience duplicate
    membershipType: MembershipType  # Convenience duplicate
    characterId: int
    dateLastPlayed: datetime
    minutesPlayedThisSession: int
    classType: CharacterType  # deprecated!
    light: int


class DictionaryComponentResponseOfint64AndDestinyCharacterComponent(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    data: Mapping[int, DestinyCharacterComponent]


class DestinyProfileResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    characters: Optional[DictionaryComponentResponseOfint64AndDestinyCharacterComponent]


class GroupUserInfoCard(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    membershipId: int
    membershipType: MembershipType
    LastSeenDisplayName: str
    LastSeenDisplayNameType: MembershipType
    bungieGlobalDisplayName: smart_optional(str)
    bungieGlobalDisplayNameCode: smart_optional(int)

    def best_name(self) -> str:
        if (self.bungieGlobalDisplayName is not None
                and self.bungieGlobalDisplayNameCode is not None):
            return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)
        return self.LastSeenDisplayName


class GroupMember(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    memberType: int
    isOnline: bool
    lastOnlineStatusChange: int
    groupId: int
    destinyUserInfo: GroupUserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    joinDate: datetime


class GroupV2(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    groupId: int
    name: str
    groupType: int
    creationDate: datetime


class GroupMembership(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    member: GroupMember
    group: GroupV2


class GroupResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    detail: GroupV2
    founder: GroupMember


class GetGroupsForMemberResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    areAllMembershipsInactive: Mapping[int, bool]
    results: Sequence[GroupMembership]


class SearchResultOfGroupMember(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    results: Sequence[GroupMember]
    hasMore: bool


class DestinyHistoricalStatsValuePair(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    value: float
    displayValue: str


class DestinyHistoricalStatsValue(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    statId: str
    basic: DestinyHistoricalStatsValuePair
    pga: Optional[DestinyHistoricalStatsValuePair] = None
    weighted: Optional[DestinyHistoricalStatsValuePair] = None
    activityId: Optional[int] = None


class DestinyHistoricalStatsActivity(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    directorActivityHash: int
    instanceId: int
    mode: GameMode
    modes: Sequence[GameMode]


class DestinyHistoricalStatsPeriodGroup(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    values: Mapping[str, DestinyHistoricalStatsValue]


class DestinyActivityHistoryResults(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    activities: Sequence[DestinyHistoricalStatsPeriodGroup]


class DestinyPostGameCarnageReportEntry(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    player: DestinyPlayer
    characterId: int


class DestinyPostGameCarnageReportData(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    entries: Sequence[DestinyPostGameCarnageReportEntry]


class UserSearchResponseDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    bungieGlobalDisplayName: str
    bungieGlobalDisplayNameCode: Optional[int]
    bungieNetMembershipId: Optional[int] = None
    destinyMemberships: Sequence[UserInfoCard]

    def combined_global_display_name(self):
        return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)


class UserSearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    searchResults: Sequence[UserSearchResponseDetail]
    page: int
    hasMore: bool
