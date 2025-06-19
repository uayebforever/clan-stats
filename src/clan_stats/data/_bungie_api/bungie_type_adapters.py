import logging
from datetime import timedelta, datetime, timezone
from typing import Dict, Any, Callable, Optional, Sequence, Mapping

from clan_stats.data._bungie_api.bungie_enums import MembershipType
from clan_stats.data._bungie_api.bungie_types import UserMembershipData, UserInfoCard, GroupMember, \
    DestinyHistoricalStatsPeriodGroup, DestinyPlayer, DestinyPostGameCarnageReportData, DestinyHistoricalStatsValue, \
    UserSearchResponseDetail
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.individuals import Player, Membership, MinimalPlayer, MinimalPlayerWithClan, \
    GroupMinimalPlayer
from clan_stats.util.itertools import only, first, is_empty
from clan_stats.util.time import TimePeriod

log = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = [
    "xbox",
    "psn",
    "fb",
    "blizzard",
    "steam",
    "stadia",
    "twitch",
    "egs",
]


def _get_platform_for_type(membership_type: MembershipType) -> str:
    if membership_type is MembershipType.XBOX:
        return "xbox"
    if membership_type is MembershipType.PSN:
        return "psn"
    if membership_type is MembershipType.STEAM:
        return "steam"
    if membership_type is MembershipType.BLIZZARD:
        return "blizzard"
    if membership_type is MembershipType.STADIA:
        return "stadia"
    if membership_type is MembershipType.EPIC_GAMES_STORE:
        return "egs"
    raise KeyError(f"Unknown platform string for membership type {membership_type}")


def _membership_has_id(membership_id: int) -> Callable[[UserInfoCard], bool]:
    def func(card: UserInfoCard) -> bool:
        return card.membershipId == membership_id

    return func


def membership_from_user_info_card(card: UserInfoCard) -> Membership:
    return Membership(
        membership_id=card.membershipId,
        membership_type=card.membershipType
    )


def find_cross_save_primary(cards: Sequence[UserInfoCard]) -> UserInfoCard:
    """From the bungie API docs
    The list of Membership Types indicating the platforms on which this Membership can be used.

    Not in Cross Save = its original membership type. Cross Save Primary = Any membership types it is overridding,
    and its original membership type Cross Save Overridden = Empty list
    """
    possible: list[UserInfoCard] = []
    for card in cards:
        if len(card.applicableMembershipTypes) == 0:
            # this one is overridden and not primary
            continue
        if len(card.applicableMembershipTypes) > 0:
            # this is cross save primary
            return card
        else:
            possible.append(card)
    # no obvious primary, just return the first one
    if len(possible) == 0:
        log.debug("User Info cards: %s", cards)
        raise RuntimeError("Could not find primary membership for cross save")
    return possible[0]


def primary_membership_from_cards(cards: Sequence[UserInfoCard]) -> Membership:
    return membership_from_user_info_card(find_cross_save_primary(cards))


def player_from_user_search_response_detail(data: UserSearchResponseDetail) -> Player:
    if is_empty(data.destinyMemberships):
         raise ValueError(f"No memberships found for response {data}")
    cross_save_primary = find_cross_save_primary(data.destinyMemberships)
    return Player(
        primary_membership=membership_from_user_info_card(cross_save_primary),
        name=data.combined_global_display_name(),
        bungie_id=data.bungieNetMembershipId,
        all_names=_get_platform_names_from_user_info_cards(data.destinyMemberships),
        is_private=not cross_save_primary.isPublic,
        last_seen=None
    )


def player_from_user_membership_data(data: UserMembershipData) -> Player:
    if data.primaryMembershipId is not None:
        membership = only(filter(
            _membership_has_id(data.primaryMembershipId),
            data.destinyMemberships))
    else:
        membership = first(data.destinyMemberships)

    return Player(
        bungie_id=data.bungieNetUser.membershipId,
        primary_membership=Membership(membership_id=membership.membershipId,
                                      membership_type=membership.membershipType),
        name=data.bungieNetUser.uniqueName,
        last_seen=data.bungieNetUser.lastUpdate,
        is_private=None,
        all_names=_get_all_platform_names(data.bungieNetUser)
    )


def player_from_group_member(group_member: GroupMember) -> GroupMinimalPlayer:
    return GroupMinimalPlayer(
        primary_membership=Membership(
            membership_id=group_member.destinyUserInfo.membershipId,
            membership_type=group_member.destinyUserInfo.membershipType),
        name=group_member.destinyUserInfo.best_name(),
        last_online=datetime.fromtimestamp(group_member.lastOnlineStatusChange, timezone.utc),
        group_join_date=group_member.joinDate)


def player_from_destiny_player(destiny_player: DestinyPlayer) -> MinimalPlayerWithClan:
    return MinimalPlayerWithClan(
        primary_membership=Membership(
            membership_id=destiny_player.destinyUserInfo.membershipId,
            membership_type=destiny_player.destinyUserInfo.membershipType),
        name=destiny_player.best_name(),
        clan_name=destiny_player.clanName)


def activity_from_destiny_activity(group: DestinyHistoricalStatsPeriodGroup) -> Activity:
    return Activity(
        instance_id=group.activityDetails.instanceId,
        director_activity_hash=group.activityDetails.directorActivityHash,
        time_period=TimePeriod(start=group.period,
                               length=timedelta(seconds=group.values["timePlayedSeconds"].basic.value)),
        primary_mode=group.activityDetails.mode,
        modes=group.activityDetails.modes,
        completed=_is_completed(group.values.get("completed"))
    )


def _is_completed(value: Optional[DestinyHistoricalStatsValue]) -> Optional[bool]:
    if value is None:
        return None
    return value.basic.value > 0


def activity_with_post(activity: Activity,
                       post: DestinyPostGameCarnageReportData
                       ) -> ActivityWithPost:
    return ActivityWithPost(
        instance_id=activity.instance_id,
        director_activity_hash=activity.director_activity_hash,
        time_period=activity.time_period,
        primary_mode=activity.primary_mode,
        modes=activity.modes,
        players=[player_from_destiny_player(p.player) for p in post.entries],
    )


def _get_all_platform_names(data):
    platform_names = {}
    for platform in SUPPORTED_PLATFORMS:
        key = f"{platform}DisplayName"
        platform_display_name = getattr(data, key)
        if platform_display_name is not None:
            platform_names[platform] = platform_display_name
    return platform_names


def _get_platform_names_from_user_info_cards(cards: Sequence[UserInfoCard]) -> Mapping[str, str]:
    return {f"{_get_platform_for_type(card.membershipType)}DisplayName": card.displayName for card in cards}
