from typing import Sequence, Optional, List

from clan_stats.data._bungie_api.bungie_types import GroupMembership


def find_clan_group(groups: Sequence[GroupMembership]) -> Optional[GroupMembership]:
    clan_type_groups: List[GroupMembership] = []
    for group in groups:
        if group.group.groupType == 1:
            clan_type_groups.append(group)
    if len(clan_type_groups) > 1:
        raise ValueError("More than one clan group in groups")
    if len(clan_type_groups) == 1:
        return clan_type_groups[0]
    return None
