from typing import Optional, Sequence

from clan_stats.clan_manager import Member
from clan_stats.data.types.individuals import Player, MinimalPlayer

from clan_stats.terminal import term
from clan_stats.ui.tables import TableBuilder
from clan_stats.util.itertools import not_empty
from clan_stats.util.optional import require_else


def print_player_list(players: Sequence[MinimalPlayer],
                      description: Optional[str] = None) -> None:
    if description is not None:
        print(description.format(count=len(players)))

    tb: TableBuilder[MinimalPlayer] = TableBuilder()

    @tb.add_column(name="Name")
    def name(player: MinimalPlayer) -> str: return player.name

    @tb.add_column(name="Membership Id")
    def mid(player: MinimalPlayer) -> str:
        return str(player.primary_membership.membership_id)

    if not_empty(players):
        print(tb.build(players))



def print_member_list(members: Sequence[Member],
                      description: Optional[str] = None) -> None:
    if description is not None:
        print(description.format(count=len(members)))

    tb: TableBuilder[Member] = TableBuilder()

    @tb.add_column(name="Name")
    def name(m: Member) -> str:
        return require_else(m.bungie_name(), "???")

    @tb.add_column(name="Membership Id")
    def mid(m: Member) -> str:
        return require_else(str(m.bungie_id()), "0")

    if not_empty(members):
        print(tb.build(members))


