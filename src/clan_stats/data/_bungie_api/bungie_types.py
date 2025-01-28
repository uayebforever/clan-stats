from typing import Optional, Sequence, Mapping
from datetime import datetime

from pydantic import BaseModel, Field

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType, GameMode


def display_name_from_name_and_code(name: str, code: int) -> str:
    return f"{name}#{code:04d}"


class GeneralUser(BaseModel):
    model_config = {"extra": "allow"}

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
    membershipType: MembershipType
    membershipId: int
    displayName: str
    applicableMembershipTypes: Sequence[int] = Field(default_factory=list)


class UserMembershipData(BaseModel):
    bungieNetUser: GeneralUser
    destinyMemberships: Sequence[UserInfoCard]

    primaryMembershipId: Optional[int] = Field(default=None)


class DestinyPlayer(BaseModel):
    model_config = {"extra": "allow"}

    destinyUserInfo: UserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    clanName: Optional[str] = Field(default=None)

    def best_name(self) -> str:
        if self.bungieNetUserInfo is not None:
            return self.bungieNetUserInfo.displayName
        return self.destinyUserInfo.displayName


class DestinyCharacterComponent(BaseModel):
    model_config = {"extra": "allow"}

    membershipId: int  # Convenience duplicate
    membershipType: MembershipType  # Convenience duplicate
    characterId: int
    dateLastPlayed: datetime
    minutesPlayedThisSession: int
    classType: CharacterType  # deprecated!
    light: int


class DictionaryComponentResponseOfint64AndDestinyCharacterComponent(BaseModel):
    model_config = {"extra": "allow"}

    data: Mapping[int, DestinyCharacterComponent]


class DestinyProfileResponse(BaseModel):
    model_config = {"extra": "allow"}

    characters: Optional[DictionaryComponentResponseOfint64AndDestinyCharacterComponent]


class GroupUserInfoCard(BaseModel):
    model_config = {"extra": "allow"}

    membershipId: int
    membershipType: MembershipType
    LastSeenDisplayName: str
    LastSeenDisplayNameType: MembershipType
    bungieGlobalDisplayName: Optional[str]
    bungieGlobalDisplayNameCode: Optional[int]

    def best_name(self) -> str:
        if (self.bungieGlobalDisplayName is not None
                and self.bungieGlobalDisplayNameCode is not None):
            return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)
        return self.LastSeenDisplayName


class GroupMember(BaseModel):
    memberType: int
    isOnline: bool
    lastOnlineStatusChange: int
    groupId: int
    destinyUserInfo: GroupUserInfoCard
    bungieNetUserInfo: Optional[UserInfoCard] = Field(default=None)
    joinDate: datetime


class GroupV2(BaseModel):
    model_config = {"extra": "allow"}

    groupId: int
    name: str
    groupType: int
    creationDate: datetime


class GroupMembership(BaseModel):
    member: GroupMember
    group: GroupV2


class GroupResponse(BaseModel):
    model_config = {"extra": "allow"}

    detail: GroupV2
    founder: GroupMember


class GetGroupsForMemberResponse(BaseModel):
    model_config = {"extra": "allow"}

    areAllMembershipsInactive: Mapping[int, bool]
    results: Sequence[GroupMembership]


class SearchResultOfGroupMember(BaseModel):
    model_config = {"extra": "allow"}

    results: Sequence[GroupMember]
    hasMore: bool


class DestinyHistoricalStatsValuePair(BaseModel):
    value: float
    displayValue: str


class DestinyHistoricalStatsValue(BaseModel):
    statId: str
    basic: DestinyHistoricalStatsValuePair
    pga: Optional[DestinyHistoricalStatsValuePair] = None
    weighted: Optional[DestinyHistoricalStatsValuePair] = None
    activityId: Optional[int] = None


class DestinyHistoricalStatsActivity(BaseModel):
    model_config = {"extra": "allow"}

    directorActivityHash: int
    instanceId: int
    mode: GameMode
    modes: Sequence[GameMode]


class DestinyHistoricalStatsPeriodGroup(BaseModel):
    model_config = {"extra": "allow"}

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    values: Mapping[str, DestinyHistoricalStatsValue]


class DestinyActivityHistoryResults(BaseModel):
    activities: Sequence[DestinyHistoricalStatsPeriodGroup]


class DestinyPostGameCarnageReportEntry(BaseModel):
    model_config = {"extra": "allow"}

    player: DestinyPlayer
    characterId: int


class DestinyPostGameCarnageReportData(BaseModel):
    model_config = {"extra": "allow"}

    period: datetime
    activityDetails: DestinyHistoricalStatsActivity
    entries: Sequence[DestinyPostGameCarnageReportEntry]


class UserSearchResponseDetail(BaseModel):
    bungieGlobalDisplayName: str
    bungieGlobalDisplayNameCode: Optional[int]
    bungieNetMembershipId: Optional[int] = None
    destinyMemberships: Sequence[UserInfoCard]

    def combined_global_display_name(self):
        return display_name_from_name_and_code(self.bungieGlobalDisplayName, self.bungieGlobalDisplayNameCode)


class UserSearchResponse(BaseModel):
    model_config = {"extra": "forbid"}

    searchResults: Sequence[UserSearchResponseDetail]
    page: int
    hasMore: bool
