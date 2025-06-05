from datetime import date
from pathlib import Path

from clan_stats.clan_manager.membership_database import MembershipDatabase
from clan_stats.clan_manager.orm_types import Member
from clan_stats.util.itertools import first
from randomdata import random_string


def test_membership_database_add():
    db = MembershipDatabase(":memory:")

    notes = random_string()
    member = Member(first_join=date.today(), notes=notes)

    assert len(db.members) == 0

    db.add_member(member)

    members = db.members

    assert len(members) == 1
    only_member = first(members)
    assert only_member.first_join == date.today()


def test_membership_database_file_add(tmp_path: Path):
    db = MembershipDatabase(tmp_path.joinpath("sqlite.db").absolute())

    notes = random_string()
    member = Member(first_join=date.today(), notes=notes)

    assert len(db.members) == 0

    db.add_member(member)

    members = db.members

    assert len(members) == 1
    only_member = first(members)
    assert only_member.first_join == date.today()
    assert only_member.notes == notes
