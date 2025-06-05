import random

from clan_stats.clan_manager.clan_membership_database import ClanMembershipDatabase, AccountType, find_unknown_players
from clan_stats.clan_manager.membership_database import MembershipDatabase
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import GroupMinimalPlayer
from clan_stats.util.itertools import only
from randomdata import random_string, random_group_minimal_player, random_character


def test_new_member_in_active_members():
    delegate = MembershipDatabase(":memory:")
    db = ClanMembershipDatabase(delegate)

    assert list(db.current_members()) == []

    bungie_id = random.randint(1, 1000)
    bungie_name = random_string()
    discord_username = random_string()

    db.new_member(bungie_primary_membership_id=bungie_id,
                  bungie_display_name=bungie_name,
                  discord_username=discord_username)

    members = list(db.current_members())
    assert len(members) == 1

    assert only(members).active_accounts("bungie_primary")[0].name == bungie_name
    assert only(members).active_accounts(AccountType.BUNGIE)[0].account_identifier == str(bungie_id)

    assert only(members).active_accounts("discord")[0].account_identifier == discord_username
    assert only(members).active_accounts(AccountType.DISCORD)[0].name == discord_username


def test_add_player_and_unknown_players():
    delegate = MembershipDatabase(":memory:")
    db = ClanMembershipDatabase(delegate)

    player_one = random_group_minimal_player()
    player_two = random_group_minimal_player()
    clan = Clan(
        id=1,
        name="clan",
        players=[
            player_one,
            player_two
        ],
        characters=[random_character(player_one), random_character(player_two)]
    )

    assert len(find_unknown_players(db, clan)) == 2

    db.new_member_for_player(clan.players[0], "discord_user")

    assert len(find_unknown_players(db, clan)) == 1

