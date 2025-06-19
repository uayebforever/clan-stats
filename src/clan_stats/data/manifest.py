import abc
import sqlite3
import json
from functools import cache

from pathlib import Path
from typing import Mapping


class Manifest(abc.ABC):

    def get_activity_name(self, activity_hash: int) -> str:
        raise NotImplementedError()


class SqliteManifest(Manifest):

    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.dbconnection = None

    def get_activity_name(self, activity_hash: int):

        activity_names = self._get_activity_name_data()
        activity_name_structure = activity_names.get(self._convert_hash(activity_hash),
                                                     {"displayProperties": {"name": f"Unknown: {activity_hash}"}})
        return activity_name_structure["displayProperties"]["name"]

    def _open_manifest(self):
        self.dbconnection = sqlite3.connect(self.manifest_path)

    def _check_loaded(self):
        if self.dbconnection is None:
            self._open_manifest()
        assert self.dbconnection is not None

    @cache
    def _get_activity_name_data(self) -> Mapping[str, str]:
        self._check_loaded()
        return {k: json.loads(v) for k, v in
                self.dbconnection.cursor().execute("SELECT * FROM DestinyActivityDefinition").fetchall()}

    def _convert_hash(self, activity_hash):
        # see https://github.com/vpzed/Destiny2-API-Info/wiki/API-Introduction-Part-3-Manifest#converting-hashes-for-the-sqlite-db
        if (activity_hash & (1 << (32 - 1))) != 0:
            return activity_hash - (1 << 32)
        else:
            return activity_hash

