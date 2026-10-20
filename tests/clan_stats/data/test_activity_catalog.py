import json
import sqlite3
from pathlib import Path

import pytest

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.activity_catalog import (ActivityCatalog, ActivityFilter, ActivityFilterError,
                                              filter_activities, fuzzy_match, initials)
from clan_stats.data.manifest import SqliteManifest
from randomdata import random_activity

RAID = int(GameMode.RAID)
DUNGEON = int(GameMode.DUNGEON)
PVE = int(GameMode.ALL_PV_E)

LW = 2122313384
VOTD_NORMAL = 1441982566
VOTD_MASTER = 4217492330
VOG_NORMAL = 3881495763
VOG_MASTER = 3022541210
SE = 1541433876
DP = 3817322389
DUALITY = 2823159265
REDACTED = 1
STRANGE_MODE = 2
CROTA = 4179289725
NO_DIRECT_MODE = 3


def _definition(hash_, name, original_name, modes, redacted=False, direct_mode=None):
    return {
        "hash": hash_,
        "displayProperties": {"name": name},
        "originalDisplayProperties": {"name": original_name},
        "directActivityModeType": modes[0] if direct_mode is None else direct_mode,
        "activityModeTypes": modes,
        "activityTypeHash": 2043403989,
        "redacted": redacted,
    }


DEFINITIONS = [
    _definition(LW, "Last Wish: Level 55", "Last Wish", [RAID, PVE]),
    _definition(VOTD_NORMAL, "Vow of the Disciple", "Vow of the Disciple", [RAID, PVE]),
    _definition(VOTD_MASTER, "Vow of the Disciple: Master", "Vow of the Disciple", [RAID, PVE]),
    _definition(VOG_NORMAL, "Vault of Glass: Normal", "Vault of Glass", [RAID, PVE]),
    _definition(VOG_MASTER, "Vault of Glass (Master)", "", [RAID, PVE]),
    _definition(SE, "Salvation's Edge", "Salvation's Edge", [RAID, PVE]),
    _definition(DP, "The Desert Perpetual", "The Desert Perpetual", [RAID, PVE]),
    _definition(DUALITY, "Duality", "Duality", [DUNGEON, PVE]),
    _definition(REDACTED, "Classified", "Classified", [RAID], redacted=True),
    _definition(STRANGE_MODE, "Mystery", "Mystery", [9999]),
    # activityModeTypes can list modes the activity does not belong to
    _definition(CROTA, "Crota's End", "Crota's End", [RAID, DUNGEON, PVE]),
    _definition(NO_DIRECT_MODE, "Fallback", "Fallback", [DUNGEON, PVE], direct_mode=0),
]


def _signed(hash_):
    return hash_ - (1 << 32) if hash_ & (1 << 31) else hash_


@pytest.fixture
def manifest(tmp_path: Path) -> SqliteManifest:
    path = tmp_path / "manifest.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE DestinyActivityDefinition (id INTEGER PRIMARY KEY NOT NULL, json BLOB)")
    connection.executemany("INSERT INTO DestinyActivityDefinition VALUES (?, ?)",
                           [(_signed(d["hash"]), json.dumps(d)) for d in DEFINITIONS])
    connection.commit()
    connection.close()
    return SqliteManifest(path)


@pytest.fixture
def catalog(manifest) -> ActivityCatalog:
    return ActivityCatalog.from_manifest(manifest)


def test_activity_definitions_split_variants(manifest):
    definitions = {d.hash: d for d in manifest.get_activity_definitions()}

    assert REDACTED not in definitions
    assert (definitions[LW].base_name, definitions[LW].variant) == ("Last Wish", "Level 55")
    assert (definitions[VOTD_NORMAL].base_name, definitions[VOTD_NORMAL].variant) == ("Vow of the Disciple", "Normal")
    assert (definitions[VOTD_MASTER].base_name, definitions[VOTD_MASTER].variant) == ("Vow of the Disciple", "Master")
    assert (definitions[VOG_MASTER].base_name, definitions[VOG_MASTER].variant) == ("Vault of Glass", "Master")
    assert definitions[LW].modes == [GameMode.RAID]
    assert definitions[CROTA].modes == [GameMode.RAID]
    assert definitions[NO_DIRECT_MODE].modes == [GameMode.DUNGEON, GameMode.ALL_PV_E]
    assert definitions[STRANGE_MODE].modes == []


def test_activity_names_still_resolve(manifest):
    assert manifest.get_activity_name(VOTD_MASTER) == "Vow of the Disciple: Master"


def test_initials():
    assert initials("Vow of the Disciple") == "votd"
    assert initials("King's Fall") == "kf"


@pytest.mark.parametrize("query", ["LW", "lw", "Wish", "last wish", "Last Wish"])
def test_fuzzy_match_last_wish(query):
    assert fuzzy_match(query, ["Last Wish", "Vow of the Disciple", "Salvation's Edge"]) == ["Last Wish"]


@pytest.mark.parametrize("query", ["Vow", "VotD", "VD", "vow of the disciple"])
def test_fuzzy_match_vow(query):
    assert fuzzy_match(query, ["Last Wish", "Vow of the Disciple", "Vault of Glass"]) == ["Vow of the Disciple"]


def test_fuzzy_match_prefers_exact_initials_over_substring():
    # "se" is also a substring of "Desert"
    assert fuzzy_match("SE", ["Salvation's Edge", "The Desert Perpetual"]) == ["Salvation's Edge"]


def test_fuzzy_match_ambiguous_and_empty():
    assert fuzzy_match("v", ["Vow of the Disciple", "Vault of Glass"]) == ["Vow of the Disciple", "Vault of Glass"]
    assert fuzzy_match("", ["a", "b"]) == ["a", "b"]
    assert fuzzy_match("zzz", ["a", "b"]) == []


def test_catalog_groups_variants(catalog):
    raids = {a.name: a for a in catalog.activities(GameMode.RAID)}

    assert raids["Vow of the Disciple"].variants == {"Master": frozenset({VOTD_MASTER}),
                                                     "Normal": frozenset({VOTD_NORMAL})}
    assert "Classified" not in raids
    assert "Crota's End" in raids
    assert "Crota's End" not in [a.name for a in catalog.activities(GameMode.DUNGEON)]
    assert GameMode.DUNGEON in catalog.types()


def test_resolve_type_only(catalog):
    assert catalog.resolve("raid") == ActivityFilter(mode=GameMode.RAID)
    assert catalog.resolve("Raid") == ActivityFilter(mode=GameMode.RAID)
    assert catalog.resolve("all-pv-e") == ActivityFilter(mode=GameMode.ALL_PV_E)


def test_resolve_activity(catalog):
    assert catalog.resolve("raid:LW") == ActivityFilter(mode=GameMode.RAID, hashes=frozenset({LW}))
    assert catalog.resolve("raid:vow") == ActivityFilter(mode=GameMode.RAID,
                                                         hashes=frozenset({VOTD_NORMAL, VOTD_MASTER}))


def test_resolve_variant(catalog):
    assert catalog.resolve("raid:VotD:master") == ActivityFilter(mode=GameMode.RAID,
                                                                 hashes=frozenset({VOTD_MASTER}))


def test_resolve_wildcard_activity(catalog):
    assert catalog.resolve("raid::master") == ActivityFilter(mode=GameMode.RAID,
                                                             hashes=frozenset({VOTD_MASTER, VOG_MASTER}))


@pytest.mark.parametrize("filter_text", ["raid:v", "raid:nothing", "nosuchtype", "raid:VotD:heroic", "a:b:c:d",
                                         "dungeon:LW"])
def test_resolve_errors(catalog, filter_text):
    with pytest.raises(ActivityFilterError):
        catalog.resolve(filter_text)


def test_ambiguous_error_lists_candidates(catalog):
    with pytest.raises(ActivityFilterError, match="Vault of Glass.*Vow of the Disciple"):
        catalog.resolve("raid:v")


def test_filter_activities():
    raid = random_activity().model_copy(update={"primary_mode": GameMode.RAID, "modes": [GameMode.RAID],
                                                "director_activity_hash": LW})
    dungeon = random_activity().model_copy(update={"primary_mode": GameMode.DUNGEON, "modes": [GameMode.DUNGEON],
                                                   "director_activity_hash": DUALITY})

    assert filter_activities([raid, dungeon], []) == [raid, dungeon]
    assert filter_activities([raid, dungeon], [ActivityFilter(mode=GameMode.RAID)]) == [raid]
    votd_master_only = ActivityFilter(mode=GameMode.RAID, hashes=frozenset({VOTD_MASTER}))
    assert filter_activities([raid, dungeon], [votd_master_only]) == []
    assert filter_activities([raid, dungeon], [ActivityFilter(mode=GameMode.RAID),
                                               ActivityFilter(mode=GameMode.DUNGEON)]) == [raid, dungeon]
