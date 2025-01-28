from clan_stats.data._bungie_api.bungie_types import GeneralUser
from randomdata import random_int, random_string


def random_general_user() -> GeneralUser:
    return GeneralUser(
        membershipId=random_int(),
        uniqueName=random_string(),
        displayName=random_string(),
        xboxDisplayName=random_string(),
    )
