import abc
import re
import sqlite3
import json
from functools import cache

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from pydantic import BaseModel, ConfigDict

from clan_stats.data._bungie_api.bungie_enums import GameMode

NORMAL_VARIANT = "Normal"
_VARIANT_STRIP_CHARACTERS = " :-\u2013\u2014()[]"


class ActivityDefinition(BaseModel):
    """The parts of a DestinyActivityDefinition needed to identify and filter activities."""
    model_config = ConfigDict(frozen=True)
    hash: int
    name: str
    base_name: str
    variant: str
    modes: Sequence[GameMode]
    activity_type_hash: Optional[int] = None


class Manifest(abc.ABC):

    def get_activity_name(self, activity_hash: int) -> str:
        raise NotImplementedError()

    def get_activity_definitions(self) -> Sequence[ActivityDefinition]:
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

    def get_activity_definitions(self) -> Sequence[ActivityDefinition]:
        definitions = (_activity_definition_from_json(blob)
                       for blob in self._get_activity_name_data().values())
        return [d for d in definitions if d is not None]

    def _open_manifest(self):
        self.dbconnection = sqlite3.connect(self.manifest_path)

    def _check_loaded(self):
        if self.dbconnection is None:
            self._open_manifest()
        assert self.dbconnection is not None

    @cache
    def _get_activity_name_data(self) -> Mapping[int, Mapping[str, Any]]:
        self._check_loaded()
        return {k: json.loads(v) for k, v in
                self.dbconnection.cursor().execute("SELECT * FROM DestinyActivityDefinition").fetchall()}

    def _convert_hash(self, activity_hash):
        # see https://github.com/vpzed/Destiny2-API-Info/wiki/API-Introduction-Part-3-Manifest#converting-hashes-for-the-sqlite-db
        if (activity_hash & (1 << (32 - 1))) != 0:
            return activity_hash - (1 << 32)
        else:
            return activity_hash


def _activity_definition_from_json(blob: Mapping[str, Any]) -> Optional[ActivityDefinition]:
    if blob.get("redacted", False):
        return None
    name = blob.get("displayProperties", {}).get("name", "").strip()
    if not name:
        return None
    base_name, variant = _split_variant(name, blob.get("originalDisplayProperties", {}).get("name", "").strip())
    return ActivityDefinition(
        hash=blob["hash"],
        name=name,
        base_name=base_name,
        variant=variant,
        modes=_game_modes(blob),
        activity_type_hash=blob.get("activityTypeHash"))


def _split_variant(name: str, original_name: str):
    """Split a display name like "Vault of Glass: Master" into its base name and variant."""
    if original_name and name.startswith(original_name):
        base_name = original_name
    elif ":" in name:
        base_name = name.split(":", 1)[0].strip()
    elif re.fullmatch(r".+\(.+\)", name):
        base_name = name[:name.rindex("(")].strip()
    else:
        base_name = name
    variant = name[len(base_name):].strip(_VARIANT_STRIP_CHARACTERS)
    return base_name, variant if variant else NORMAL_VARIANT


def _game_modes(blob: Mapping[str, Any]) -> Sequence[GameMode]:
    mode_values = list(blob.get("activityModeTypes") or [])
    if blob.get("directActivityModeType") is not None:
        mode_values.insert(0, blob["directActivityModeType"])
    modes = []
    for value in mode_values:
        try:
            mode = GameMode(value)
        except ValueError:
            continue
        if mode != GameMode.NONE and mode not in modes:
            modes.append(mode)
    return modes
