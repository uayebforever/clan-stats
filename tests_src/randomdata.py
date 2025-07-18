import random
import string
from datetime import datetime, timezone, timedelta
from enum import Enum, IntEnum
from functools import partial
from typing import TypeVar, Type, Callable, Sequence, Optional

from clan_stats.data._bungie_api.bungie_enums import MembershipType, CharacterType, GameMode, ClanMemberType
from clan_stats.data.types.activities import Activity, ActivityWithPost
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import Player, Membership, MinimalPlayer, Character, GroupMinimalPlayer, \
    MinimalPlayerWithClan
from clan_stats.util.itertools import flatten
from clan_stats.util.time import now, TimePeriod

_T = TypeVar("_T")


def random_string(length: int = 8) -> str:
    return "".join(random.sample(string.ascii_letters, length))


def random_int(max=100000000) -> int:
    return random.randint(0, max)


def random_datetime() -> datetime:
    return datetime.fromtimestamp(now().timestamp() - random_int(1_000_000), timezone.utc)


_T_Enum = TypeVar("_T_Enum", bound=Enum)


def random_enum(enum: Type[_T_Enum]) -> _T_Enum:
    return random.choice(list(enum))


def random_excluding(random_provider: Callable[[], _T], excluding: Sequence[_T]) -> _T:
    attempts = 1
    value = random_provider()
    while value in excluding and attempts < 1000:
        value = random_provider()
    if value in excluding:
        raise RuntimeError("random_excluding: unable to find satisfactory random value")
    return value


def random_player() -> Player:
    return Player(
        primary_membership=random_membership(),
        name=random_string(),
        bungie_id=random_int(),
        is_private=False,
        last_seen=None,
        all_memberships=None,
    )


def random_group_minimal_player() -> GroupMinimalPlayer:
    return GroupMinimalPlayer(
        primary_membership=random_membership(),
        name=random_string(),
        last_online=random_datetime(),
        group_join_date=random_datetime(),
        group_membership_type=random_enum(ClanMemberType)
    )


def random_membership():
    return Membership(membership_id=random_int(),
                      membership_type=random_enum(MembershipType))


def random_character(player: MinimalPlayer) -> Character:
    return Character(
        membership=random_membership(),
        character_id=random_int(),
        character_type=random_enum(CharacterType),
        power_level=random_int(),
        player=player)


def random_group_minimal_player() -> GroupMinimalPlayer:
    return GroupMinimalPlayer(
        primary_membership=random_membership(),
        name=random_string(),
        last_online=random_datetime(),
        group_join_date=random_datetime(),
        group_membership_type=random_enum(ClanMemberType))


def random_clan() -> Clan:
    players = [random_group_minimal_player(),
               random_group_minimal_player(),
               random_group_minimal_player()]
    characters = flatten([[random_character(p), random_character(p)] for p in players])
    return Clan(
        id=random_int(),
        name=random_string(),
        players=players,
        characters=characters)


def random_activity() -> Activity:
    primary = random_enum(GameMode)
    return Activity(
        instance_id=random_int(),
        director_activity_hash=random_int(),
        time_period=TimePeriod(start=random_datetime(), length=timedelta(seconds=random_int(2000))),
        primary_mode=primary,
        modes=[random_excluding(partial(random_enum, GameMode), [primary]), primary]
    )


def random_post_activity(activity: Optional[Activity] = None) -> ActivityWithPost:
    if activity is None:
        activity = random_activity()
    return ActivityWithPost(
        players=[random_minimal_player_with_clan(), random_minimal_player_with_clan()],
        **activity.model_dump(mode="python")
    )


def random_minimal_player_with_clan():
    return MinimalPlayerWithClan(
        primary_membership=random_membership(),
        name=random_string(),
        clan_name=random_string())
