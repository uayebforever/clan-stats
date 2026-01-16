from enum import IntEnum
from typing import final


class EnumReprMixin:

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class MembershipType(EnumReprMixin, IntEnum):
    NONE = 0
    XBOX = 1
    PSN = 2
    STEAM = 3
    BLIZZARD = 4
    STADIA = 5
    EPIC_GAMES_STORE = 6
    DEMON = 10
    BUNGIE = 254
    ALL = -1


class CharacterType(EnumReprMixin, IntEnum):
    TITAN = 0
    HUNTER = 1
    WARLOCK = 2
    UNKNOWN = 3


class GameMode(EnumReprMixin, IntEnum):
    """An Enum for all available gamemodes in Destiny 2."""

    NONE = 0
    """_No description given by bungie._ """
    STORY = 2
    """_No description given by bungie._ """
    STRIKE = 3
    """_No description given by bungie._ """
    RAID = 4
    """_No description given by bungie._ """
    ALL_PV_P = 5
    """_No description given by bungie._ """
    PATROL = 6
    """_No description given by bungie._ """
    ALL_PV_E = 7
    """_No description given by bungie._ """
    RESERVED9 = 9
    """_No description given by bungie._ """
    CONTROL = 10
    """_No description given by bungie._ """
    RESERVED11 = 11
    """_No description given by bungie._ """
    CLASH = 12
    """Clash -> Destiny's name for Team Deathmatch. 4v4 combat, the team with the highest kills at the end of time wins. """
    RESERVED13 = 13
    """_No description given by bungie._ """
    CRIMSON_DOUBLES = 15
    """_No description given by bungie._ """
    NIGHTFALL = 16
    """_No description given by bungie._ """
    HEROIC_NIGHTFALL = 17
    """_No description given by bungie._ """
    ALL_STRIKES = 18
    """_No description given by bungie._ """
    IRON_BANNER = 19
    """_No description given by bungie._ """
    RESERVED20 = 20
    """_No description given by bungie._ """
    RESERVED21 = 21
    """_No description given by bungie._ """
    RESERVED22 = 22
    """_No description given by bungie._ """
    RESERVED24 = 24
    """_No description given by bungie._ """
    ALL_MAYHEM = 25
    """_No description given by bungie._ """
    RESERVED26 = 26
    """_No description given by bungie._ """
    RESERVED27 = 27
    """_No description given by bungie._ """
    RESERVED28 = 28
    """_No description given by bungie._ """
    RESERVED29 = 29
    """_No description given by bungie._ """
    RESERVED30 = 30
    """_No description given by bungie._ """
    SUPREMACY = 31
    """_No description given by bungie._ """
    PRIVATE_MATCHES_ALL = 32
    """_No description given by bungie._ """
    SURVIVAL = 37
    """_No description given by bungie._ """
    COUNTDOWN = 38
    """_No description given by bungie._ """
    TRIALS_OF_THE_NINE = 39
    """_No description given by bungie._ """
    SOCIAL = 40
    """_No description given by bungie._ """
    TRIALS_COUNTDOWN = 41
    """_No description given by bungie._ """
    TRIALS_SURVIVAL = 42
    """_No description given by bungie._ """
    IRON_BANNER_CONTROL = 43
    """_No description given by bungie._ """
    IRON_BANNER_CLASH = 44
    """_No description given by bungie._ """
    IRON_BANNER_SUPREMACY = 45
    """_No description given by bungie._ """
    SCORED_NIGHTFALL = 46
    """_No description given by bungie._ """
    SCORED_HEROIC_NIGHTFALL = 47
    """_No description given by bungie._ """
    RUMBLE = 48
    """_No description given by bungie._ """
    ALL_DOUBLES = 49
    """_No description given by bungie._ """
    DOUBLES = 50
    """_No description given by bungie._ """
    PRIVATE_MATCHES_CLASH = 51
    """_No description given by bungie._ """
    PRIVATE_MATCHES_CONTROL = 52
    """_No description given by bungie._ """
    PRIVATE_MATCHES_SUPREMACY = 53
    """_No description given by bungie._ """
    PRIVATE_MATCHES_COUNTDOWN = 54
    """_No description given by bungie._ """
    PRIVATE_MATCHES_SURVIVAL = 55
    """_No description given by bungie._ """
    PRIVATE_MATCHES_MAYHEM = 56
    """_No description given by bungie._ """
    PRIVATE_MATCHES_RUMBLE = 57
    """_No description given by bungie._ """
    HEROIC_ADVENTURE = 58
    """_No description given by bungie._ """
    SHOWDOWN = 59
    """_No description given by bungie._ """
    LOCKDOWN = 60
    """_No description given by bungie._ """
    SCORCHED = 61
    """_No description given by bungie._ """
    SCORCHED_TEAM = 62
    """_No description given by bungie._ """
    GAMBIT = 63
    """_No description given by bungie._ """
    ALL_PV_E_COMPETITIVE = 64
    """_No description given by bungie._ """
    BREAKTHROUGH = 65
    """_No description given by bungie._ """
    BLACK_ARMORY_RUN = 66
    """_No description given by bungie._ """
    SALVAGE = 67
    """_No description given by bungie._ """
    IRON_BANNER_SALVAGE = 68
    """_No description given by bungie._ """
    PV_P_COMPETITIVE = 69
    """_No description given by bungie._ """
    PV_P_QUICKPLAY = 70
    """_No description given by bungie._ """
    CLASH_QUICKPLAY = 71
    """_No description given by bungie._ """
    CLASH_COMPETITIVE = 72
    """_No description given by bungie._ """
    CONTROL_QUICKPLAY = 73
    """_No description given by bungie._ """
    CONTROL_COMPETITIVE = 74
    """_No description given by bungie._ """
    GAMBIT_PRIME = 75
    """_No description given by bungie._ """
    RECKONING = 76
    """_No description given by bungie._ """
    MENAGERIE = 77
    """_No description given by bungie._ """
    VEX_OFFENSIVE = 78
    """_No description given by bungie._ """
    NIGHTMARE_HUNT = 79
    """_No description given by bungie._ """
    ELIMINATION = 80
    """_No description given by bungie._ """
    MOMENTUM = 81
    """_No description given by bungie._ """
    DUNGEON = 82
    """_No description given by bungie._ """
    SUNDIAL = 83
    """_No description given by bungie._ """
    TRIALS_OF_OSIRIS = 84
    """_No description given by bungie._ """
    DARES = 85
    """_No description given by bungie._ """
    OFFENSIVE = 86
    """_No description given by bungie._ """
    LOST_SECTOR = 87
    """_No description given by bungie._ """
    RIFT = 88
    """_No description given by bungie._ """
    ZONE_CONTROL = 89
    """_No description given by bungie._ """
    IRON_BANNER_RIFT = 90
    """_No description given by bungie._ """
    IRON_BANNER_ZONE_CONTROL = 91
    """_No description given by bungie._ """
    RELIC = 92
    """_No description given by bungie._ """
    LAWLESS_FRONTIER = 93
    """_No description given by bungie._ """



@final
class ClanMemberType(IntEnum):
    """An enum for bungie clan member types."""

    NONE = 0
    BEGINNER = 1
    MEMBER = 2
    ADMIN = 3
    ACTING_FOUNDER = 4
    FOUNDER = 5
