import asyncio
import logging
from datetime import date
from typing import Tuple, Callable, Optional, Dict, NamedTuple

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Grid
from textual.reactive import reactive
from textual.widgets import DataTable, Header, Footer, Label, Rule, Input, TextArea

from clan_stats.clan_manager import ClanMembershipDatabase, AccountType, Member, Account
from clan_stats.clan_manager.clan_membership_database import find_unknown_players
from clan_stats.clan_manager.membership_database import MembershipDatabase
from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import GroupMinimalPlayer
from clan_stats.util.itertools import only, first
from clan_stats.util.optional import require_else

EDITING = "editing"

log = logging.getLogger(__name__)


def interactive_clan_list(clan_id: int, data_retriever: DataRetriever):
    clan = asyncio.run(_fetch_clan_data(data_retriever, clan_id))
    clan_database = ClanMembershipDatabase(MembershipDatabase(ClanMembershipDatabase.path(clan_id)))

    InteractiveClanList(clan_database, clan).run(loop=asyncio.new_event_loop())


class UnknownPlayersTable(DataTable, can_focus=True):
    BINDINGS = [
        ("a", 'app.add', "Add player as new member")
    ]


class EscInput(Input):

    def on_key(self, event: events.Key):
        if event.key != "escape":
            super()._on_key(event)

class MemberEditor(Vertical):
    BINDINGS = [
        ("ctrl+s", 'save', "Save member"),
        ("escape", 'escape', "Cancel and return to list"),
    ]

    bungie_name = reactive("")
    bungie_id = reactive("")
    discord_name = reactive("")

    def __init__(self, clan_database: ClanMembershipDatabase, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clan_database = clan_database
        self._grid: Optional[Grid] = None
        self._fields: Dict[str, Input] = {}
        self._member: Optional[Member] = None

    def add_field(self, title: str, /, id: str, disabled: bool = False):
        field = EscInput(id=id, disabled=disabled)
        field.border_title = title
        if title in self._fields:
            raise ValueError(f"Field {title} already exists!")
        self._fields[id] = field
        return field

    def compose(self) -> ComposeResult:
        with Grid(id="basics") as grid:
            grid.styles.grid_size_columns = 2  # Two columns
            grid.styles.grid_rows = (3,)  # three lines per row
            yield self.add_field("Bungie Name", id="bungie_name", disabled=True)
            yield self.add_field("Discord Username", id="discord_name")
            yield self.add_field("Bungie Membership Number", id="bungie_id", disabled=True)
            yield self.add_field("Date joined", id="joined")
        yield TextArea(id="member_notes")

    def watch_bungie_name(self, bungie_name: str):
        self._fields["bungie_name"].value = bungie_name

    def watch_discord_name(self, bungie_name: str):
        self._fields["discord_name"].value = bungie_name

    def watch_bungie_id(self, bungie_id: str):
        self._fields["bungie_id"].value = bungie_id

    def action_save(self):
        if self._member is None:
            raise RuntimeError
        discord_account = only(self._member.active_accounts(AccountType.DISCORD))
        discord_account.name = self._fields["discord_name"].value
        discord_account.account_identifier = self._fields["discord_name"].value
        self._clan_database.save_changes()
        self.run_action('app.end_edit')
        self._member = None

    def action_escape(self):
        self._clan_database.cancel_chages()
        self._member = None
        self.run_action('app.end_edit')

    def action_update(self, member: Member):
        bungie = only(member.active_accounts(AccountType.BUNGIE))
        discord = only(member.active_accounts(AccountType.DISCORD))
        self._member = member
        self.bungie_name = bungie.name
        self.discord_name = discord.account_identifier
        self.bungie_id = bungie.account_identifier
        self._fields["joined"].value = member.first_join.isoformat()


class InteractiveClanList(App):
    CSS_PATH = "interactive_clan_list.tcss"

    _active_columns: Tuple[str, Callable[[Member], str]] = (
        ("Bungie Name", lambda m: only(m.active_accounts(AccountType.BUNGIE)).name),
        ("Discord", lambda m: only(m.active_accounts(AccountType.DISCORD)).name),
        ("Joined", lambda m: m.first_join.isoformat()),
        ("Notes", lambda m: truncate_str(require_else(m.notes, ""), 40)),
    )

    _unknown_columns: Tuple[str, Callable[[GroupMinimalPlayer], str]] = (
        ("Bungie Name", lambda p: p.name),
        ("Bungie ID", lambda p: str(p.primary_membership.membership_id)),
        ("Last online", lambda p: p.last_online.date().isoformat()),
        ("Joined", lambda p: p.group_join_date.date().isoformat()),
    )

    def __init__(self, clan_database: ClanMembershipDatabase, clan: Clan):
        super().__init__()
        self._clan = clan
        self._clan_database = clan_database

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="list"):
            with Vertical(classes="area"):
                yield Label("Unknown Players from Bungie Clan")
                yield UnknownPlayersTable(id="unknown")
            with Vertical(classes="area"):
                yield Label("Current Members")
                yield DataTable(id="active")
            with Vertical(classes="area"):
                yield Label("Past Members")
                yield DataTable(id="past")
        yield MemberEditor(self._clan_database, id="edit")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_unknown()
        self._populate_active()

    def action_add(self):
        table = self.query_one("#unknown", DataTable)
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        player_to_add = only(p for p in self._clan.players if str(p.primary_membership.membership_id) == key)
        log.info("Adding player % to clan", player_to_add)
        member = self._clan_database.new_member(
            bungie_primary_membership_id=player_to_add.primary_membership.membership_id,
            bungie_display_name=player_to_add.name,
            discord_username=f"discord_{player_to_add.name}",
            join_date=player_to_add.group_join_date.date()
        )

        self.edit_member(member)
        # Edit member will call updates if the edit is saved.

    def _populate_unknown(self):
        table = self.query_one("#unknown", DataTable)
        for column_name, _ in self._unknown_columns:
            table.add_column(column_name)

        self._update_unknown()

    def _update_unknown(self):
        unknown_players = find_unknown_players(self._clan_database, self._clan)
        table = self.query_one("#unknown", DataTable)

        for player in unknown_players:
            table.add_row(*(lam(player) for _, lam in self._unknown_columns),
                          key=str(player.primary_membership.membership_id))

    def _populate_active(self):
        table = self.query_one("#active", DataTable)

        for column_name, _ in self._active_columns:
            table.add_column(column_name)

        self._update_active()

    def _update_active(self):
        table = self.query_one("#active", DataTable)
        table.clear()
        for member in self._clan_database.current_members():
            table.add_row(*(lam(member) for _, lam in self._active_columns))

    def _populate_past(self):
        table = self.query_one("#past", DataTable)

        columns = (
            ("Bungie Name", lambda m: only(m.active_accounts(AccountType.BUNGIE)).name),
            ("Discord", lambda m: only(m.active_accounts(AccountType.DISCORD)).name),
            ("Joined", lambda m: m.first_join.isoformat()),
            ("Notes", lambda m: truncate_str(require_else(m.notes, ""), 40)),
        )

        for column_name, _ in columns:
            table.add_column(column_name)

        for member in self._clan_database.past_members():
            table.add_row(*(lam(member) for _, lam in columns))

    def edit_member(self, member: Member):
        # self.query_one("#list", Vertical).add_class("editing")
        editor = self.query_one("#edit", MemberEditor)
        # editor.add_class("editing")
        self.add_class(EDITING)
        editor.action_update(member)

    def action_end_edit(self):
        # self.query_one("#list", Vertical).remove_class(EDITING)
        editor = self.query_one("#edit", MemberEditor)
        # editor.remove_class("editing")
        self.remove_class(EDITING)


def truncate_str(text: str, length: int) -> str:
    if len(text) > length:
        return text[:length - 2] + "…"
    else:
        return text


async def _fetch_clan_data(data_retriever: DataRetriever, clan_id: int, mode: GameMode = GameMode.NONE
                           ) -> Clan:
    # ) -> Tuple[Clan, Mapping[str, Optional[datetime]]]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        # last_active = await get_most_recent_activity(data_retriever, clan.players, mode=mode)
    return clan
