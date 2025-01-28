from datetime import timedelta, datetime, timezone
from typing import Dict, Any, Callable, Optional, Sequence

from clan_stats.data._bungie_api.bungie_types import UserMembershipData, UserInfoCard, GroupMember, \
    DestinyHistoricalStatsPeriodGroup, DestinyPlayer, DestinyPostGameCarnageReportData, DestinyHistoricalStatsValue
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.individuals import Player, Membership, MinimalPlayer, MinimalPlayerWithClan, \
    GroupMinimalPlayer
from clan_stats.util.itertools import only, first
from clan_stats.util.time import TimePeriod

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


def _membership_has_id(membership_id: int) -> Callable[[UserInfoCard], bool]:
    def func(card: UserInfoCard) -> bool:
        return card.membershipId == membership_id

    return func


def membership_from_user_info_card(card: UserInfoCard) -> Membership:
    return Membership(
        membership_id=card.membershipId,
        membership_type=card.membershipType
    )


def primary_membership_from_cards(cards: Sequence[UserInfoCard]) -> Membership:
    """From the bungie API docs
    The list of Membership Types indicating the platforms on which this Membership can be used.

    Not in Cross Save = its original membership type. Cross Save Primary = Any membership types it is overridding,
    and its original membership type Cross Save Overridden = Empty list
    """
    possible = []
    for cards in cards:
        if len(cards.applicableMembershipTypes) == 0:
            # this one is overridden and not primary
            continue
        if len(cards.applicableMembershipTypes) > 1:
            # this is cross save primary
            return membership_from_user_info_card(cards)
        else:
            possible.append(cards)
    # no obvious primary, just return the first one
    return membership_from_user_info_card(possible[0])


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


def player_from_bungie_destiny_memberships(data: Dict[str, Any]) -> Player:
    return Player(
        bungie_id=data["membershipId"],
        member_type="",
        last_seen_name=data["uniqueName"],
        last_on_destiny=None,
        is_private=None,
        all_names=_get_all_platform_names(data)

    )


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
