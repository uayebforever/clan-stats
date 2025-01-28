from typing import List, Sequence

from pydantic import BaseModel

from .individuals import Player, Character, GroupMinimalPlayer
from ...util.itertools import first


class Clan(BaseModel):
    id: int
    name: str
    players: Sequence[GroupMinimalPlayer]
    characters: Sequence[Character]

    def find_player_with_id(self, member_id) -> Player:
        return first(filter(lambda p: p.member_id == member_id, self.players))

    def player_by_name(self, name) -> Player:
        return first(filter(lambda p: p.name == name, self.players))

    def characters_for_player(self, member_id) -> List[Character]:
        return list(filter(lambda c: c.member_id == member_id, self.characters))

    def find_player_for_character(self, character_id) -> Player:
        character = self.character_from_id(character_id)
        return self.find_player_with_id(character.member_id)

    def character_from_id(self, character_id) -> Character:
        return first(filter(lambda c: c.character_id == character_id, self.characters))
