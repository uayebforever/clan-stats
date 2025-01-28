import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class DiscordMember(object):
    charlemagne_name: str
    discord_id: str


@dataclass
class DiscordGroup(object):
    members: List[DiscordMember]

    def get_player(self, discord_id: str) -> str:
        index = [m.discord_id for m in self.members].index(discord_id)
        return self.members[index].charlemagne_name

    def get_discord(self, player_name: str) -> str:
        index = [m.charlemagne_name for m in self.members].index(player_name)
        return self.members[index].discord_id

    def __contains__(self, item: DiscordMember) -> bool:
        return item in self.members


def group_from_csv_file(filename: Path) -> DiscordGroup:
    members: List[DiscordMember] = list()
    with (open(filename, "r", newline="") as f):
        reader = csv.reader(f, delimiter=",", skipinitialspace=True, escapechar="\\")
        for row in reader:
            if len(row) == 2:
                bungie, discord = row
            elif len(row) == 3:
                bungie, discord, leave_date = row
            elif len(row) > 3:
                bungie, discord, leave_date, comment = row[:4]

            if bungie.startswith("#"):
                # Ignore comment lines.
                continue
            if leave_date == "":
                members.append(DiscordMember(bungie, discord))
    return DiscordGroup(members)


def group_from_copy_paste_file(filename: str) -> DiscordGroup:
    with open(filename, 'r') as f:
        file_contents = [l.strip() for l in f.readlines()]
    members: List[DiscordMember] = list()
    for bungie, discord in zip(file_contents[0::2], file_contents[1::2]):
        members.append(DiscordMember(bungie, discord))
    return DiscordGroup(members)
