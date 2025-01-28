from clan_stats.data._bungie_api.bungie_enums import MembershipType
from clan_stats.data._bungie_api.bungie_type_adapters import player_from_user_membership_data
from clan_stats.data._bungie_api.bungie_types import UserMembershipData, GeneralUser, UserInfoCard
from random_bungie_data import random_general_user
from randomdata import random_int, random_string, random_enum, random_excluding


def test_player_from_user_membership_data():
    member_type_1 = random_enum(MembershipType)
    member_type_2 = random_excluding(lambda: random_enum(MembershipType),
                                     [member_type_1])
    user = UserMembershipData(
        bungieNetUser=random_general_user(),
        destinyMemberships=[
            UserInfoCard(
                membershipType=member_type_1,
                membershipId=random_int(),
                displayName=random_string()),
            UserInfoCard(
                membershipType=member_type_2,
                membershipId=random_int(),
                displayName=random_string())])

    player = player_from_user_membership_data(user)

    assert player.bungie_id == user.bungieNetUser.membershipId
