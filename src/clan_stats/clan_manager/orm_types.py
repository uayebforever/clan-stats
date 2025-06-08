from enum import StrEnum
from typing import Sequence, Optional

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

from clan_stats.util.itertools import first
from clan_stats.util.optional import map_optional

Base = declarative_base()


class AccountType(StrEnum):
    BUNGIE = "bungie_primary"
    DISCORD = "discord"


class Member(Base):
    __tablename__ = "member"

    id = Column(Integer, primary_key=True)

    first_join = Column(Date)
    notes = Column(Text)

    accounts = relationship('Account', back_populates='member', cascade="all, delete-orphan")
    membership_history = relationship('MembershipStatus', back_populates='member', cascade="all, delete-orphan")

    def current_status(self) -> 'MembershipStatus':
        return first(sorted(self.membership_history, key=lambda s: s.date_conferred, reverse=True))

    def active_accounts(self, type: str) -> Sequence['Account']:
        return [a for a in self.all_accounts(type) if a.is_active]

    def all_accounts(self, type: str) -> Sequence['Account']:
        return [a for a in self.accounts if a.account_type == type]

    def _primary_bungie_account(self) -> Optional['Account']:
        bungie_accounts = self.active_accounts(AccountType.BUNGIE)
        if len(bungie_accounts) == 0:
            return None
        return bungie_accounts[0]

    def _primary_discord_account(self) -> Optional['Account']:
        discord_accounts = self.active_accounts(AccountType.DISCORD)
        if len(discord_accounts) == 0:
            return None
        return discord_accounts[0]

    def bungie_id(self) -> Optional[int]:
        return int(map_optional(self._primary_bungie_account(), lambda m: m.account_identifier))

    def bungie_name(self) -> Optional[str]:
        return map_optional(self._primary_bungie_account(), lambda m: m.name)

    def discord_name(self) -> Optional[str]:
        return map_optional(self._primary_discord_account(), lambda m: m.name)


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey(f"{Member.__tablename__}.id"), nullable=False)
    member = relationship('Member', back_populates='accounts')

    account_type = Column(String)
    name = Column(String)
    account_identifier = Column(String)
    is_active = Column(Boolean, default=True)
    note = Column(Text)


class MembershipStatus(Base):
    __tablename__ = "membership_status"

    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey(f"{Member.__tablename__}.id"), nullable=False)
    member = relationship('Member', back_populates='membership_history')

    status = Column(String)
    date_conferred = Column(Date)
    notes = Column(Text)
