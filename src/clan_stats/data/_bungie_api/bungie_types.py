from datetime import datetime
from typing import Optional, Sequence, Mapping, Any, Annotated

import bungio
import bungio.models
from pydantic import BaseModel, Field, ConfigDict, AliasGenerator, AliasChoices, BeforeValidator, field_validator
from pydantic_core import PydanticUseDefault

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType, GameMode
from clan_stats.util.casing import to_snake_case


def display_name_from_name_and_code(name: str, code: int) -> str:
    return f"{name}#{code:04d}"


validation_aliases = AliasGenerator(
    validation_alias=lambda field_name: AliasChoices(field_name, to_snake_case(field_name))
)
ALLOW_EXTRA = ConfigDict(extra="allow", from_attributes=True, alias_generator=validation_aliases)


def unexpectedly_missing_string(value: Any) -> Any:  # pyright: ignore [reportExplicitAny, reportAny]
    if value is bungio.models.MISSING or value is None:
        return "???"
    return value  # pyright: ignore [reportAny]


class BungieTypeBase(BaseModel):

    @field_validator('*', mode='before')
    @classmethod
    def default_value_validator(cls, value: Any) -> Any:  # pyright: ignore [reportExplicitAny, reportAny]
        """This validator matches special default values provided by e.g. Bungio API"""
        if value is bungio.models.MISSING:
            raise PydanticUseDefault()
        return value  # pyright: ignore [reportAny]


class GeneralUser(BungieTypeBase):
    model_config = ALLOW_EXTRA

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


class UserInfoCard(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    membershipType: MembershipType
    membershipId: int

    # For some reason, long running activities with many players have a Post game with missing names.
    displayName: Annotated[str, BeforeValidator(unexpectedly_missing_string)]

    # applicableMembershipTypes: smart_optional(Sequence[int]) = Field(default_factory=list)
    applicableMembershipTypes: Any = Field(default_factory=list)


class GroupUserInfoCard(BungieTypeBase):
    # https://bungie-net.github.io/#/components/schemas/GroupsV2.GroupUserInfoCard
    model_config = ALLOW_EXTRA

    membershipId: int
    membershipType: MembershipType
    LastSeenDisplayName: str
    LastSeenDisplayNameType: MembershipType
    bungieGlobalDisplayName: Optional[str]
    bungieGlobalDisplayNameCode: Optional[int]
    displayName: str
    applicableMembershipTypes: Sequence[MembershipType]

    def best_name(self) -> str:
        if (self.bungieGlobalDisplayName is not None
                and self.bungieGlobalDisplayNameCode is not None):
            return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)
        return self.LastSeenDisplayName


class UserMembershipData(BungieTypeBase):
    # https://bungie-net.github.io/#/components/schemas/User.UserMembershipData
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    bungieNetUser: Optional[GeneralUser] = None
    destinyMemberships: Sequence[GroupUserInfoCard]

    primaryMembershipId: Optional[int] = Field(default=None)


class DestinyPlayer(BungieTypeBase):
    model_config = ALLOW_EXTRA

    destinyUserInfo: UserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    clanName: Optional[str] = Field(default=None)

    def best_name(self) -> str:
        if self.bungieNetUserInfo is not None:
            return self.bungieNetUserInfo.displayName
        return self.destinyUserInfo.displayName


class DestinyCharacterComponent(BungieTypeBase):
    model_config = ALLOW_EXTRA

    membershipId: int  # Convenience duplicate
    membershipType: MembershipType  # Convenience duplicate
    characterId: int
    dateLastPlayed: datetime
    minutesPlayedThisSession: int
    classType: CharacterType  # deprecated!
    light: int


class DictionaryComponentResponseOfint64AndDestinyCharacterComponent(BungieTypeBase):
    model_config = ALLOW_EXTRA

    data: Mapping[int, DestinyCharacterComponent]


class DestinyProfileResponse(BungieTypeBase):
    model_config = ALLOW_EXTRA

    characters: Optional[DictionaryComponentResponseOfint64AndDestinyCharacterComponent]


class DestinyManifest(BungieTypeBase):
    model_config = ALLOW_EXTRA

    version: str
    mobileWorldContentPaths: Mapping[str, str]


class GroupMember(BungieTypeBase):
    # https://bungie-net.github.io/#/components/schemas/GroupsV2.GroupMember
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    memberType: int
    isOnline: bool
    lastOnlineStatusChange: int
    groupId: int
    destinyUserInfo: GroupUserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    joinDate: datetime


class GroupV2(BungieTypeBase):
    model_config = ALLOW_EXTRA

    groupId: int
    name: str
    groupType: int
    creationDate: datetime


class GroupMembership(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    member: GroupMember
    group: GroupV2


class GroupResponse(BungieTypeBase):
    model_config = ALLOW_EXTRA

    detail: GroupV2
    founder: GroupMember


class GetGroupsForMemberResponse(BungieTypeBase):
    model_config = ALLOW_EXTRA

    areAllMembershipsInactive: Mapping[int, bool]
    results: Sequence[GroupMembership]


class SearchResultOfGroupMember(BungieTypeBase):
    model_config = ALLOW_EXTRA

    results: Sequence[GroupMember]
    hasMore: bool


class DestinyHistoricalStatsValuePair(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    value: float
    displayValue: str


class DestinyHistoricalStatsValue(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    statId: str
    basic: DestinyHistoricalStatsValuePair
    pga: Optional[DestinyHistoricalStatsValuePair] = None
    weighted: Optional[DestinyHistoricalStatsValuePair] = None
    activityId: Optional[int] = None


class DestinyHistoricalStatsActivity(BungieTypeBase):
    model_config = ALLOW_EXTRA

    directorActivityHash: int
    instanceId: int
    mode: GameMode
    modes: Sequence[GameMode]


class DestinyHistoricalStatsPeriodGroup(BungieTypeBase):
    model_config = ALLOW_EXTRA

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    values: Mapping[str, DestinyHistoricalStatsValue]


class DestinyActivityHistoryResults(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    activities: Optional[Sequence[DestinyHistoricalStatsPeriodGroup]] = Field(default_factory=list)


class DestinyPostGameCarnageReportEntry(BungieTypeBase):
    model_config = ALLOW_EXTRA

    player: DestinyPlayer
    characterId: int


class DestinyPostGameCarnageReportData(BungieTypeBase):
    model_config = ALLOW_EXTRA

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    activityWasStartedFromBeginning: Optional[bool]
    entries: Sequence[DestinyPostGameCarnageReportEntry]


class UserSearchResponseDetail(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    bungieGlobalDisplayName: str
    bungieGlobalDisplayNameCode: Optional[int]
    bungieNetMembershipId: Optional[int] = None
    destinyMemberships: Sequence[UserInfoCard]

    def combined_global_display_name(self):
        return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)


class UserSearchResponse(BungieTypeBase):
    model_config = ConfigDict(from_attributes=True, alias_generator=validation_aliases)

    searchResults: Sequence[UserSearchResponseDetail]
    page: int
    hasMore: bool
