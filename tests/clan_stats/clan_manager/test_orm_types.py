from datetime import date

from clan_stats.clan_manager.orm_types import Member, MembershipStatus, Account


def test_membership_history():
    member = Member(
        first_join=date.today(),
        membership_history=[
            MembershipStatus(
                date_conferred=date(2020, 1, 1),
                status="Probationary"),
            MembershipStatus(
                date_conferred=date(2020, 3, 1),
                status="Full"),
            MembershipStatus(
                date_conferred=date(2024, 1, 1),
                status="Kicked"),
        ]
    )

    assert len(member.membership_history) ==3

    assert member.current_status().status == "Kicked"


def test_accounts():

    member = Member(
        first_join=date.today(),
        accounts=[
            Account(
                account_type="bungie_primary",
                account_identifier="1234"),
            Account(
                account_type="discord",
                account_identifier="discordusername"),
        ]
    )

    assert set(map(lambda a: a.account_type, member.accounts)) == {"bungie_primary", "discord"}

