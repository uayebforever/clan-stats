from datetime import date
from enum import StrEnum
from typing import Sequence, Optional, final

# @formatter:off
from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean  # pyright: ignore [reportMissingImports, reportUnknownVariableType]
from sqlalchemy.orm import declarative_base, relationship  # pyright: ignore [reportMissingImports, reportUnknownVariableType]
# @formatter:on

from clan_stats.util.itertools import first
from clan_stats.util.optional import map_optional

Base = declarative_base()  # pyright: ignore [reportUnknownVariableType]


class AccountType(StrEnum):
    BUNGIE = "bungie_primary"
    DISCORD = "discord"


@final
class Member(Base):  # pyright: ignore [reportUntypedBaseClass]
    __tablename__ = "member"

    # @formatter:off
    id: int = Column(Integer, primary_key=True)  # pyright: ignore [reportUnknownVariableType]

    first_join: date = Column(Date)  # pyright: ignore [reportUnknownVariableType]
    notes: str = Column(Text)  # pyright: ignore [reportUnknownVariableType]

    accounts: Sequence['Account'] = relationship('Account', back_populates='member', cascade="all, delete-orphan")  # pyright: ignore [reportUnknownVariableType]
    membership_history: Sequence['MembershipStatus'] = relationship('MembershipStatus', back_populates='member', cascade="all, delete-orphan")  # pyright: ignore [reportUnknownVariableType]
    # @formatter:on

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
        return map_optional(self._primary_bungie_account(), lambda m: int(m.account_identifier))

    def bungie_name(self) -> Optional[str]:
        return map_optional(self._primary_bungie_account(), lambda m: m.name)

    def discord_name(self) -> Optional[str]:
        return map_optional(self._primary_discord_account(), lambda m: m.name)


@final
class Account(Base):  # pyright: ignore [reportUntypedBaseClass]
    __tablename__ = "account"

    # @formatter:off
    id: int = Column(Integer, primary_key=True)  # pyright: ignore [reportUnknownVariableType]
    member_id: int = Column(Integer, ForeignKey(f"{Member.__tablename__}.id"), nullable=False)  # pyright: ignore [reportUnknownVariableType]
    member: Member = relationship('Member', back_populates='accounts')  # pyright: ignore [reportUnknownVariableType]

    account_type: str = Column(String)  # pyright: ignore [reportUnknownVariableType]
    name: str = Column(String)  # pyright: ignore [reportUnknownVariableType]
    account_identifier: str = Column(String)  # pyright: ignore [reportUnknownVariableType]
    is_active: bool = Column(Boolean, default=True)  # pyright: ignore [reportUnknownVariableType]
    note: str = Column(Text)  # pyright: ignore [reportUnknownVariableType]
    # @formatter:on


@final
class MembershipStatus(Base):  # pyright: ignore [reportUntypedBaseClass]
    __tablename__ = "membership_status"

    # @formatter:off
    id: int = Column(Integer, primary_key=True) # pyright: ignore [reportUnknownVariableType]
    member_id: int = Column(Integer, ForeignKey(f"{Member.__tablename__}.id"), nullable=False) # pyright: ignore [reportUnknownVariableType]
    member: Member = relationship('Member', back_populates='membership_history') # pyright: ignore [reportUnknownVariableType]

    status: str = Column(String) # pyright: ignore [reportUnknownVariableType]
    date_conferred: date = Column(Date) # pyright: ignore [reportUnknownVariableType]
    notes: str = Column(Text) # pyright: ignore [reportUnknownVariableType]
    # @formatter:on
