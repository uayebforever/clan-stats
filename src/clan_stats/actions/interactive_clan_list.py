import asyncio
import logging
from datetime import date
from typing import Tuple, Callable, Optional, Dict, NamedTuple, Sequence, ClassVar, TypeVar, Generic, ParamSpec

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Grid
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import DataTable, Header, Footer, Label, Rule, Input, TextArea

from clan_stats.clan_manager import ClanMembershipDatabase, AccountType, Member, Account, MembershipStatus
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

P = ParamSpec("P")


def interactive_clan_list(clan_id: int, data_retriever: DataRetriever):
    clan = asyncio.run(_fetch_clan_data(data_retriever, clan_id))
    clan_database = ClanMembershipDatabase(MembershipDatabase(ClanMembershipDatabase.path(clan_id)))

    InteractiveClanList(clan_database, clan).run(loop=asyncio.new_event_loop())


class UnknownPlayersTable(DataTable, can_focus=True):
    BINDINGS = [
        ("a", 'app.add', "Add player as new member")
    ]


class MembersTable(DataTable, can_focus=True):
    BINDINGS = [
        ("e", 'app.edit', "Edit member")
    ]


class EscapableInput(Input):
    """Input that bubbles the escape key up rather than eating it."""

    def on_key(self, event: events.Key):
        if event.key != "escape":
            super()._on_key(event)


_R = TypeVar('_R')


class UpdatingTable(DataTable, Generic[_R]):
    COLUMNS: ClassVar[Sequence[Tuple[str, Callable[[_R], str]]]] = []

    def on_mount(self):
        for column_head, _ in self.COLUMNS:
            self.add_column(column_head)
        self.cursor_type = "row"

    def update(self, row_list: Sequence[_R]) -> None:
        self.clear()
        self._row_sources = {}
        for i, row in enumerate(row_list):
            row_key = self.add_row(*(lam(row) for _, lam in self.COLUMNS),
                                   key=str(i))
            self._row_sources[row_key] = row

    def selected_object(self) -> _R:
        return self._row_sources[self.coordinate_to_cell_key(self.cursor_coordinate).row_key]


class SavableInput(EscapableInput):

    def __init__(self, label: str, save_hook: Callable[[str], None], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.save_hook = save_hook
        self.label = label

    def on_mount(self):
        self.border_title = self.label

    def save(self):
        self.save_hook(self.value)


class EditMemberHistoryScreen(ModalScreen):
    BINDINGS = [
        ('ctrl+s', 'save', "Save changes"),
        ('escape', 'cancel', "Cancel without saving changes")
    ]

    def __init__(self, status: MembershipStatus, **kwargs):
        super().__init__(**kwargs)
        self.status = status

    def on_mount(self):
        self.add_class("modal")

    def compose(self) -> ComposeResult:
        def save_status(value: str):
            self.status.status = value

        def save_date(value: str):
            self.status.date_conferred = date.fromisoformat(value)

        def save_notes(value: str):
            self.status.notes = value

        yield Header()
        with Grid(classes="modal") as g:
            yield Label(f"Editing Membership status")
            yield SavableInput(
                value=self.status.status,
                label="Status",
                save_hook=save_status)
            yield SavableInput(
                value=self.status.date_conferred.isoformat(),
                label="Date Conferred",
                save_hook=save_date
            )

            yield SavableInput(
                value=self.status.notes,
                label="Notes",
                save_hook=save_notes
            )
        yield Footer()

    def action_save(self):
        inputs = self.query(SavableInput)
        for input in inputs:
            input.save()
        self.dismiss("save")

    def action_cancel(self):
        self.dismiss("cancel")


class EditMemberAccountsScreen(ModalScreen):
    BINDINGS = [
        ('ctrl+s', 'save', "Save changes"),
        ('escape', 'cancel', "Cancel without saving changes")
    ]

    def __init__(self, account: Account, **kwargs):
        super().__init__(**kwargs)
        self._account = account

    def compose(self) -> ComposeResult:
        def save_type(value: str):
            self._account.account_type = value
        def save_name(value: str):
            self._account.name = value
        def save_id(value: str):
            self._account.account_identifier = value
        def save_note(value: str):
            self._account.note = value

        yield Header()
        with Grid(classes="modal") as g:
            yield Label(f"Editing Member Account")
            yield SavableInput(
                value=self._account.account_type,
                label="Account Type",
                save_hook=save_type)
            yield SavableInput(
                value=self._account.name,
                label="Display Name",
                save_hook=save_name
            )
            yield SavableInput(
                value=self._account.account_identifier,
                label="Account Unique Identifier",
                save_hook=save_id
            )
            yield SavableInput(
                value=self._account.note,
                label="Notes",
                save_hook=save_note
            )
        yield Footer()

    def action_save(self):
        inputs = self.query(SavableInput)
        for input in inputs:
            input.save()
        self.dismiss("save")

    def action_cancel(self):
        self.dismiss("cancel")


class MemberHistoryTable(UpdatingTable):
    COLUMNS: ClassVar[Sequence[Tuple[str, Callable[[MembershipStatus], str]]]] = (
        ("Status", lambda m: m.status),
        ("Date Conferred", lambda m: m.date_conferred),
        ("Notes", lambda m: truncate_str(require_else(m.notes, ""), 20)),
    )

    BINDINGS = [
        ('e', 'edit', "Edit"),
        ('a', 'add', "Add new status"),
    ]

    def __init__(self, member: Member, **kwargs):
        super().__init__(**kwargs)
        self.member = member

    def on_mount(self):
        self.border_title = "Member History"

    def action_edit(self):
        self.app.push_screen(EditMemberHistoryScreen(self.selected_object()),
                             callback=lambda result: self.update(self.member.membership_history))

    def action_add(self):
        new_status = MembershipStatus(
            member=self.member,
            status="",
            date_conferred=date.today(),
        )
        self.add_row(new_status)
        self.app.push_screen(EditMemberHistoryScreen(new_status),
                             callback=lambda result: self.update(self.member.membership_history))


class MemberAccountsTable(UpdatingTable):
    COLUMNS: ClassVar[Sequence[Tuple[str, Callable[[Account], str]]]] = [
        ("Type", lambda a: a.account_type),
        ("Name", lambda a: a.name),
        ("Act", lambda a: "A" if a.is_active else ""),
        ("Notes", lambda a: a.note)
    ]

    BINDINGS = [
        ('e', 'edit', "Edit"),
        ('a', 'add', "Add new status"),
    ]

    def __init__(self, member: Member, **kwargs):
        super().__init__(**kwargs)
        self.member = member

    def on_mount(self):
        self.border_title = "Accounts"

    def action_edit(self):
        self.app.push_screen(EditMemberAccountsScreen(self.selected_object()),
                             callback=lambda result: self.update(self.member.accounts))

    def action_add(self):
        new_status = Account(
            member=self.member,
            account_type="",
            name="",
            account_identifier="",
            is_active=False
        )
        self.add_row(new_status)
        self.app.push_screen(EditMemberAccountsScreen(new_status),
                             callback=lambda result: self.update(self.member.accounts))


class MemberEditor(Screen):
    BINDINGS = [
        ("ctrl+s", 'save', "Save member"),
        ("escape", 'escape', "Cancel and return to list"),
    ]

    bungie_name = reactive("")
    bungie_id = reactive("")
    discord_name = reactive("")

    def __init__(self, clan_database: ClanMembershipDatabase, member: Member, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clan_database = clan_database
        self._member: Member = member

        self._grid: Optional[Grid] = None
        self._fields: Dict[str, Input] = {}
        self.history_table: Optional[MemberHistoryTable] = None
        self.accounts_table: Optional[MemberAccountsTable] = None

    def add_field(self, title: str, /, id: str, disabled: bool = False):
        field = EscapableInput(id=id, disabled=disabled)
        field.border_title = title
        if title in self._fields:
            raise ValueError(f"Field {title} already exists!")
        self._fields[id] = field
        return field

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical() as base_vert:
            with Horizontal() as grid:
                with Vertical():
                    yield self.add_field("Bungie Name", id="bungie_name", disabled=True)
                    yield self.add_field("Discord Username", id="discord_name")
                    yield self.add_field("Bungie Membership Number", id="bungie_id", disabled=True)
                    yield self.add_field("Date joined", id="joined")
                yield TextArea(id="member_notes")
            with Horizontal() as horiz:
                self.history_table = MemberHistoryTable(self._member)
                yield self.history_table
                self.accounts_table = MemberAccountsTable()
                yield self.accounts_table
        yield Footer()

    def on_mount(self):
        bungie = only(self._member.active_accounts(AccountType.BUNGIE))
        discord = only(self._member.active_accounts(AccountType.DISCORD))
        self.bungie_name = bungie.name
        self.discord_name = discord.account_identifier
        self.bungie_id = bungie.account_identifier
        self._fields["joined"].value = self._member.first_join.isoformat()

        self.history_table.update(self._member.membership_history)
        self.accounts_table.update(self._member.accounts)

    def watch_bungie_name(self, bungie_name: str):
        self._fields["bungie_name"].value = bungie_name

    def watch_discord_name(self, bungie_name: str):
        self._fields["discord_name"].value = bungie_name

    def watch_bungie_id(self, bungie_id: str):
        self._fields["bungie_id"].value = bungie_id

    def action_save(self):
        discord_account = only(self._member.active_accounts(AccountType.DISCORD))
        discord_account.name = self._fields["discord_name"].value
        discord_account.account_identifier = self._fields["discord_name"].value
        self._clan_database.save_changes()
        self.dismiss()

    def action_escape(self):
        self._clan_database.cancel_chages()
        self.dismiss()


class InteractiveClanList(App):
    CSS_PATH = "interactive_clan_list.tcss"

    BINDINGS = [
        ('q', 'quit', "Exit"),
    ]

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
                yield MembersTable(id="active")
            with Vertical(classes="area"):
                yield Label("Past Members")
                yield MembersTable(id="past")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_unknown()
        self._populate_active()

    async def action_add(self):
        table = self.query_one("#unknown", UnknownPlayersTable)
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        player_to_add = only(p for p in self._clan.players if str(p.primary_membership.membership_id) == key)
        log.info("Adding player % to clan", player_to_add)
        member = self._clan_database.new_member(
            bungie_primary_membership_id=player_to_add.primary_membership.membership_id,
            bungie_display_name=player_to_add.name,
            discord_username="",
            join_date=player_to_add.group_join_date.date()
        )

        await self.edit_member(member)

    async def action_edit(self):
        table = self.query_one("#active", MembersTable)
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        member = only(m for m in self._clan_database.all_members() if str(m.id) == key)

        await self.edit_member(member)

    def _populate_unknown(self):
        table = self.query_one("#unknown", DataTable)
        table.cursor_type = 'row'
        for column_name, _ in self._unknown_columns:
            table.add_column(column_name)

        self._update_unknown()

    def _update_unknown(self):
        unknown_players = find_unknown_players(self._clan_database, self._clan)
        table = self.query_one("#unknown", DataTable)
        prev_coord = table.cursor_coordinate
        table.clear()

        for player in unknown_players:
            table.add_row(*(lam(player) for _, lam in self._unknown_columns),
                          key=str(player.primary_membership.membership_id))
        if prev_coord.row > table.row_count - 1:
            table.cursor_coordinate = Coordinate(table.row_count - 1, 0)
        else:
            table.cursor_coordinate = prev_coord

    def _populate_active(self):
        table = self.query_one("#active", DataTable)
        table.cursor_type = 'row'

        for column_name, _ in self._active_columns:
            table.add_column(column_name)

        self._update_active()

    def _update_active(self):
        table = self.query_one("#active", DataTable)
        prev_coord = table.cursor_coordinate
        table.clear()

        for member in self._clan_database.current_members():
            table.add_row(*(lam(member) for _, lam in self._active_columns), key=str(member.id))
        if prev_coord.row > table.row_count - 1:
            table.cursor_coordinate = Coordinate(table.row_count - 1, 0)
        else:
            table.cursor_coordinate = prev_coord

    def _populate_past(self):
        table = self.query_one("#past", DataTable)
        table.cursor_type = 'row'

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

    def _update_all(self):
        self._update_unknown()
        self._update_active()

    async def edit_member(self, member: Member):
        await self.push_screen(
            MemberEditor(self._clan_database, member=member),
            callback=lambda resut: self._update_all())


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
