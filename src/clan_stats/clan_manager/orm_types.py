from typing import Sequence

from sqlalchemy import Column, Integer, String, Date, Text, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship

from clan_stats.util.itertools import first

Base = declarative_base()


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
