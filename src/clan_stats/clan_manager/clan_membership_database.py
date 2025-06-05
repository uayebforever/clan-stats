from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Sequence, Iterator, Collection, Optional

from clan_stats.clan_manager.membership_database import MembershipDatabase
from clan_stats.clan_manager.orm_types import Member, MembershipStatus, Account
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import GroupMinimalPlayer
from clan_stats.util.itertools import only


class Status(StrEnum):
    NEW = "new"
    MEMBER = "member"
    ADMIN = "admin"
    FOUNDER = "founder"
    KICKED = "kicked"
    BANNED = "banned"

    @classmethod
    def active_statuses(cls) -> Collection['Status']:
        return cls.NEW, cls.MEMBER, cls.ADMIN, cls.FOUNDER


class AccountType(StrEnum):
    BUNGIE = "bungie_primary"
    DISCORD = "discord"


class ClanMembershipDatabase:

    @classmethod
    def path(cls, clan_id: int, base_path: Path = Path(".")):
        return base_path.joinpath(f"{clan_id}.sqlite")

    def __init__(self, delegate: MembershipDatabase):
        self.delegate = delegate

    def current_members(self) -> Iterator[Member]:
        for member in self.delegate.members:
            if member.current_status().status in Status.active_statuses():
                yield member

    def past_members(self) -> Iterator[Member]:
        for member in self.delegate.members:
            if member.current_status().status not in Status.active_statuses():
                yield member

    def all_members(self) -> Iterator[Member]:
        yield from self.current_members()
        yield from self.past_members()

    def save_changes(self):
        self.delegate.commit_changes()

    def cancel_chages(self):
        self.delegate.rollback_changes()

    def new_member_for_player(self, player: GroupMinimalPlayer, discord_username: str) -> Member:
        member = Member(
            first_join=player.group_join_date.date(),
            membership_history=[
                MembershipStatus(
                    date_conferred=player.group_join_date.date(),
                    status=Status.NEW),
            ],
            accounts=[
                Account(account_type=AccountType.DISCORD,
                        account_identifier=discord_username,
                        name=discord_username),
                Account(account_type=AccountType.BUNGIE,
                        account_identifier=str(player.primary_membership.membership_id),
                        name=player.name),
            ]
        )
        self.delegate.add_member(member)
        return member

    def new_member(self,
                   /,
                   bungie_primary_membership_id: int,
                   bungie_display_name: str,
                   discord_username: str,
                   join_date: Optional[date] = None
                   ) -> Member:
        if join_date is None:
            join_date = date.today()
        member = Member(
            first_join=join_date,
            membership_history=[
                MembershipStatus(
                    date_conferred=join_date,
                    status=Status.NEW),
            ],
            accounts=[
                Account(account_type=AccountType.DISCORD,
                        account_identifier=discord_username,
                        name=discord_username),
                Account(account_type=AccountType.BUNGIE,
                        account_identifier=str(bungie_primary_membership_id),
                        name=bungie_display_name),
            ]
        )
        self.delegate.add_member(member)
        return member


def find_unknown_players(clan_database: ClanMembershipDatabase,
                         bungie_clan: Clan) -> Sequence[GroupMinimalPlayer]:
    known_bungie_ids = [
        only(m.active_accounts(AccountType.BUNGIE)).account_identifier for m in clan_database.all_members()]
    unknown_players = [
        p for p in bungie_clan.players if str(p.primary_membership.membership_id) not in known_bungie_ids
    ]
    return unknown_players
