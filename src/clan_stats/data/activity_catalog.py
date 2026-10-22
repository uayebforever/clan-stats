"""A catalog of Destiny activities built from the manifest, used to resolve activity filters.

Filters have the form ``TYPE[:ACTIVITY[:VARIANT]]``, e.g. ``raid``, ``raid:LW`` or ``raid:VotD:master``.
TYPE is a GameMode name. ACTIVITY and VARIANT are matched fuzzily: by full name, word initials, or a
substring of the name. An empty ACTIVITY or VARIANT segment matches everything.
"""
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, TypeVar

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.manifest import ActivityDefinition, Manifest
from clan_stats.data.types.activities import Activity
from clan_stats.exceptions import UserError

_T = TypeVar('_T')


class ActivityFilterError(UserError):
    pass


def normalize(text: str) -> str:
    """Lowercase, drop apostrophes and treat any other punctuation as a word break."""
    text = re.sub(r"['’]", "", text.lower())
    return " ".join(re.split(r"[^a-z0-9]+", text)).strip()


def initials(text: str) -> str:
    return "".join(word[0] for word in normalize(text).split())


def _is_initials_abbreviation(query: str, name: str) -> bool:
    """True if the letters of query appear in order among the word initials of name, starting with the first."""
    name_initials = initials(name)
    if " " in query or not name_initials or query[0] != name_initials[0]:
        return False
    remaining = iter(name_initials)
    return all(letter in remaining for letter in query)


def fuzzy_match(query: str, candidates: Iterable[_T], name: Callable[[_T], str] = str) -> List[_T]:
    """Return the candidates matching query.

    In order of preference: an exact name match, an exact initials match, then any candidate whose name
    contains query or whose word initials contain the letters of query in order (e.g. "VD" for "Vow of the
    Disciple"). Only the most preferred non-empty group is returned.
    """
    candidates = list(candidates)
    q = normalize(query)
    if not q:
        return candidates
    tiers: Sequence[Callable[[str], bool]] = (
        lambda n: normalize(n) == q,
        lambda n: initials(n) == q,
        lambda n: q in normalize(n) or _is_initials_abbreviation(q, n),
    )
    for matches in tiers:
        result = [c for c in candidates if matches(name(c))]
        if result:
            return result
    return []


def mode_name(mode: GameMode) -> str:
    return mode.name.lower()


@dataclass(frozen=True)
class CatalogActivity:
    name: str
    mode: GameMode
    variants: Mapping[str, FrozenSet[int]]

    @property
    def hashes(self) -> FrozenSet[int]:
        return frozenset().union(*self.variants.values())


@dataclass(frozen=True)
class ActivityFilter:
    """Matches activities of a mode, optionally limited to particular director activity hashes."""
    mode: GameMode
    hashes: Optional[FrozenSet[int]] = None

    def matches(self, activity: Activity) -> bool:
        if self.hashes is not None:
            return activity.director_activity_hash in self.hashes
        return activity.primary_mode == self.mode or self.mode in activity.modes


def filter_activities(activities: Sequence[Activity], filters: Sequence[ActivityFilter]) -> List[Activity]:
    """Keep activities matching any of the filters. No filters keeps everything."""
    if not filters:
        return list(activities)
    return [a for a in activities if any(f.matches(a) for f in filters)]


class ActivityCatalog:

    def __init__(self, definitions: Iterable[ActivityDefinition]):
        grouped: Dict[Tuple[GameMode, str], Dict[str, Set[int]]] = defaultdict(lambda: defaultdict(set))
        for definition in definitions:
            for mode in definition.modes:
                grouped[(mode, definition.base_name)][definition.variant].add(definition.hash)

        self._activities: Dict[GameMode, List[CatalogActivity]] = defaultdict(list)
        for (mode, name), variants in sorted(grouped.items(), key=lambda i: (i[0][0], i[0][1].lower())):
            self._activities[mode].append(
                CatalogActivity(name=name, mode=mode,
                                variants={v: frozenset(h) for v, h in sorted(variants.items())}))

    @classmethod
    def from_manifest(cls, manifest: Manifest) -> 'ActivityCatalog':
        return cls(manifest.get_activity_definitions())

    def types(self) -> Sequence[GameMode]:
        return sorted(self._activities.keys(), key=mode_name)

    def activities(self, mode: GameMode) -> Sequence[CatalogActivity]:
        return self._activities.get(mode, [])

    def search(self, text: str, modes: Optional[Sequence[GameMode]] = None) -> Sequence[CatalogActivity]:
        result = []
        for mode in (modes if modes is not None else self.types()):
            result.extend(fuzzy_match(text, self.activities(mode), name=lambda a: a.name))
        return result

    def resolve_type(self, text: str) -> GameMode:
        key = text.strip().lower().replace("-", "_")
        for mode in GameMode:
            if mode_name(mode) == key:
                return mode
        matches = fuzzy_match(text, self.types(), name=lambda m: mode_name(m).replace("_", " "))
        return _only(matches, f"activity type '{text}'", lambda m: mode_name(m),
                     "clan-stats activities types")

    def resolve(self, filter_text: str) -> ActivityFilter:
        parts = filter_text.split(":")
        if len(parts) > 3:
            raise ActivityFilterError(
                f"Invalid filter '{filter_text}': expected TYPE[:ACTIVITY[:VARIANT]]")
        type_text, activity_text, variant_text = (parts + ["", ""])[:3]
        mode = self.resolve_type(type_text)
        if not activity_text.strip() and not variant_text.strip():
            return ActivityFilter(mode=mode)

        list_hint = f"clan-stats activities list {mode_name(mode)}"
        activities = fuzzy_match(activity_text, self.activities(mode), name=lambda a: a.name)
        if activity_text.strip():
            activities = [_only(activities, f"{mode_name(mode)} activity '{activity_text}'",
                                lambda a: a.name, list_hint)]

        hashes: Set[int] = set()
        for activity in activities:
            variants = fuzzy_match(variant_text, activity.variants.keys())
            if activity_text.strip() and variant_text.strip():
                variants = [_only(variants, f"variant '{variant_text}' of {activity.name}", str, list_hint)]
            for variant in variants:
                hashes.update(activity.variants[variant])
        if not hashes:
            raise ActivityFilterError(f"Filter '{filter_text}' matches no activities. See: {list_hint}")
        return ActivityFilter(mode=mode, hashes=frozenset(hashes))

    def resolve_all(self, filter_texts: Optional[Sequence[str]]) -> Sequence[ActivityFilter]:
        return [self.resolve(f) for f in (filter_texts or [])]


def _only(matches: Sequence[_T], description: str, name: Callable[[_T], str], list_hint: str) -> _T:
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ActivityFilterError(f"No {description} found. See: {list_hint}")
    raise ActivityFilterError(
        f"Ambiguous {description}, could be any of: {', '.join(name(m) for m in matches)}")
