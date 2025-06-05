import urllib
from pathlib import Path
from typing import Sequence, Optional
from urllib.parse import urlencode

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from clan_stats.clan_manager.orm_types import Base, Member


class MembershipDatabase:
    _database = "sqlite+pysqlite:///"

    def __init__(self, database_path: Path | str):
        self._database_url = self._get_database_url(database_path)
        self._connected = False
        self._engine = None
        self._session: Optional[Session] = None
        self._members: Optional[Sequence[Member]] = None

    def connect(self):

        if self._connected:
            return

        self._engine = create_engine(self._database_url, future=True)

        Base.metadata.create_all(self._engine)
        self._connected = True
        self._session = Session(self._engine, future=True)

    @property
    def members(self) -> Sequence[Member]:
        if self._members is None:
            self.connect()
            self._update_members()
        return self._members

    def add_member(self, member: Member):
        self.connect()
        self._session.add(member)
        self._update_members()

    def commit_changes(self):
        self._session.commit()

    def rollback_changes(self):
        self._session.rollback()

    def _update_members(self):
        result = self._session.execute(select(Member)).all()
        self._members = [r[0] for r in result]

    def _get_database_url(self, database_path):
        if isinstance(database_path, Path):
            url_encode_path = urllib.parse.quote(str(database_path))
            database_url = f"{self._database}{url_encode_path}"
        else:
            database_url = f"{self._database}{database_path}"
        return database_url
