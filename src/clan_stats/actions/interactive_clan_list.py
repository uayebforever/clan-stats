import asyncio
import itertools
import logging
from contextlib import contextmanager
from datetime import date
from typing import Tuple, Callable, Optional, Dict, Sequence, ClassVar, TypeVar, Generic, ParamSpec, Iterator

from pydantic import BaseModel
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Grid
from textual.coordinate import Coordinate
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.validation import Length
from textual.widgets import DataTable, Header, Footer, Label, Input, TextArea, Pretty
from textual.widgets._data_table import ColumnKey

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


def interactive_clan_list(clan_id: int, data_retriever: DataRetriever):
    log.info("Interactive clan list")
    log.info(__name__)
    clan = asyncio.run(_fetch_clan_data(data_retriever, clan_id))
    clan_database = ClanMembershipDatabase(MembershipDatabase(ClanMembershipDatabase.path(clan_id)))

    InteractiveClanList(clan_database, clan).run(loop=asyncio.new_event_loop())


_T = TypeVar("_T")
_R = TypeVar('_R')


class ColumnSpec(BaseModel, Generic[_R]):
    name: str
    data_supplier: Callable[[_R], str]
    width: Optional[int] = None


class UpdatingTable(DataTable, Generic[_R]):
    COLUMNS: ClassVar[Sequence[ColumnSpec]] = []

    BINDINGS = [
        ("s", 'sort', "Change sort"),
        ("S", 'reverse_sort', "Reverse sort"),
    ]

    DEFAULT_SORT: ClassVar[int] = 0

    @contextmanager
    def _save_excursion(self):
        old_coordinate = self.cursor_coordinate
        yield

        # Restore sorting
        if self.current_sort is not None:
            self.current_sort = self.current_sort[0], not self.current_sort[1]
            self.action_reverse_sort()

        if self.row_count == 0:
            pass
        elif old_coordinate.row > self.row_count - 1:
            self.cursor_coordinate = Coordinate(self.row_count - 1, 0)
        else:
            self.cursor_coordinate = old_coordinate

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_sort: Optional[Tuple[ColumnKey, bool]] = None
        self.sort_list: Optional[Iterator[ColumnKey]] = None

    def on_mount(self):
        log.debug("Mounting table %s", self.name)
        for colspec in self.COLUMNS:
            self.add_column(colspec.name, width=colspec.width)
        self.cursor_type = "row"
        for _ in range(require_else(self.DEFAULT_SORT, -1) + 1):
            self.action_sort()

    def update(self, row_list: Sequence[_R]) -> None:
        log.info("Updating table %s with %s %s objects",
                 self.name,
                 len(row_list),
                 first(row_list).__class__.__name__ if len(row_list) > 0 else "?")
        with self._save_excursion():
            self.clear()
            self._row_sources = {}
            for i, row in enumerate(row_list):
                row_key = self.add_row(*(cs.data_supplier(row) for cs in self.COLUMNS),
                                       key=str(i))
                self._row_sources[row_key] = row

    def selected_object(self) -> _R:
        return self._row_sources[self.coordinate_to_cell_key(self.cursor_coordinate).row_key]

    def action_sort(self):
        if self.sort_list is None:
            self.sort_list = itertools.cycle(self.columns.keys())
        self.current_sort = (next(self.sort_list), False)
        self.sort(self.current_sort[0], key=lambda v: str(v).lower())
        log.debug("Sorting table %s by column % and reverse=%s",
                  self.name, self.current_sort[0].value, self.current_sort[1])

    def action_reverse_sort(self):
        if self.sort_list is None or self.current_sort is None:
            self.action_sort()
        self.current_sort = self.current_sort[0], not self.current_sort[1]
        self.sort(self.current_sort[0], reverse=self.current_sort[1], key=lambda v: str(v).lower())
        log.debug("Sorting table %s by column % and reverse=%s",
                  self.name, self.current_sort[0].value, self.current_sort[1])


class EscapableInput(Input):
    """Input that bubbles the escape key up rather than eating it."""

    def on_key(self, event: events.Key):
        if event.key != "escape":
            super()._on_key(event)


class SavableInput(EscapableInput):

    def __init__(self, label: str, save_hook: Callable[[str], None], *args, **kwargs):
        super().__init__(*args, select_on_focus=False, **kwargs)
        self.save_hook = save_hook
        self.label = label

    def on_mount(self):
        self.border_title = self.label

    def save(self):
        self.save_hook(self.value)


class UpdateRequired(Message):
    pass


class UnknownPlayersTable(UpdatingTable[GroupMinimalPlayer]):
    BINDINGS = [
        ("a", 'add', "Add player as new member")
    ]

    COLUMNS: ClassVar[Sequence[ColumnSpec[GroupMinimalPlayer]]] = [
        ColumnSpec(name="Bungie Name", data_supplier=lambda p: p.name),
        ColumnSpec(name="Bungie ID", data_supplier=lambda p: str(p.primary_membership.membership_id)),
        ColumnSpec(name="Last online", data_supplier=lambda p: p.last_online.date().isoformat()),
        ColumnSpec(name="Joined", data_supplier=lambda p: p.group_join_date.date().isoformat()),
    ]

    def __init__(self, membership_database: ClanMembershipDatabase, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._membership_database = membership_database

    def action_add(self):
        player_to_add = self.selected_object()
        log.info("Adding player % to clan", player_to_add)
        member = self._membership_database.new_member(
            bungie_primary_membership_id=player_to_add.primary_membership.membership_id,
            bungie_display_name=player_to_add.name,
            discord_username="",
            join_date=player_to_add.group_join_date.date()
        )

        self.app.push_screen(
            MemberEditor(self._membership_database, member=member),
            callback=lambda result: self.app._update_all())

    def update(self, row_list: Sequence[GroupMinimalPlayer]) -> None:
        super().update(row_list)
        if len(row_list) == 0:
            area = self.query_ancestor(".area", Vertical)
            area.add_class("hidden")
            self.disabled = True
        else:
            area = self.query_ancestor(".area", Vertical)
            area.remove_class("hidden")
            self.disabled = False

class MembersTable(UpdatingTable[Member]):
    BINDINGS = [
        ("e", 'edit', "Edit member"),
        ("a", 'add', "Add member"),
    ]

    COLUMNS: ClassVar[Sequence[ColumnSpec[Member]]] = (
        ColumnSpec(name="Bungie Name", data_supplier=lambda m: only(m.active_accounts(AccountType.BUNGIE)).name),
        ColumnSpec(name="Discord", data_supplier=lambda m: only(m.active_accounts(AccountType.DISCORD)).name),
        ColumnSpec(name="Joined", data_supplier=lambda m: m.first_join.isoformat()),
        ColumnSpec(name="Status", data_supplier=lambda m: m.current_status().status),
        ColumnSpec(name="Notes", data_supplier=lambda m: truncate_str(require_else(m.notes, ""), 40)),
    )

    def __init__(self, membership_database: ClanMembershipDatabase, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._membership_database = membership_database

    def action_edit(self):
        member = self.selected_object()

        self.app.push_screen(
            MemberEditor(self._membership_database, member=member),
            callback=lambda result: self.app._update_all())

    def action_add(self):
        log.info("Adding new member manually")
        member = self._membership_database.new_member(
            bungie_primary_membership_id=0,
            bungie_display_name="",
            discord_username="",
            join_date=date.today()
        )

        self.app.push_screen(
            MemberEditor(self._membership_database, member=member),
            callback=lambda result: self.app._update_all())


def list_with_inserted(original_list: Sequence[_T], item: _T, index: int):
    copy = list(original_list)
    copy[index:index] = [item]
    return copy


class PastMembersTable(MembersTable):
    COLUMNS = list_with_inserted(
        MembersTable.COLUMNS,
        ColumnSpec(name="Date", data_supplier=lambda m: m.current_status().date_conferred.isoformat()),
        -1)

    DEFAULT_SORT = len(COLUMNS) - 2


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
        with Grid(classes="modal"):
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
        for field in inputs:
            field.save()
        self.dismiss("save")

    def action_cancel(self):
        self.dismiss("cancel")


class MemberHistoryTable(UpdatingTable):
    COLUMNS: ClassVar[Sequence[ColumnSpec[MembershipStatus]]] = [
        ColumnSpec(name="Status", data_supplier=lambda m: m.status, width=15),
        ColumnSpec(name="Date Conferred", data_supplier=lambda m: m.date_conferred, width=14),
        ColumnSpec(name="Notes", data_supplier=lambda m: require_else(m.notes, "")),
    ]

    BINDINGS = [
        ('e', 'edit', "Edit"),
        ('a', 'add', "Add new status"),
    ]

    def __init__(self, member: Member, database: ClanMembershipDatabase, **kwargs):
        super().__init__(**kwargs)
        self.clan_database = database
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
        self.clan_database.add_object(new_status)
        self.add_row(new_status)
        self.app.push_screen(EditMemberHistoryScreen(new_status),
                             callback=lambda result: self.update(self.member.membership_history))


class MemberAccountsTable(UpdatingTable):
    COLUMNS: ClassVar[Sequence[ColumnSpec[Account]]] = [
        ColumnSpec(name="Type", data_supplier=lambda a: a.account_type, width=10),
        ColumnSpec(name="Name", data_supplier=lambda a: a.name, width=30),
        ColumnSpec(name="Act", data_supplier=lambda a: "A" if a.is_active else "", width=3),
        ColumnSpec(name="Notes", data_supplier=lambda a: a.note)
    ]

    BINDINGS = [
        ('e', 'edit', "Edit"),
        ('a', 'add', "Add new status"),
    ]

    def __init__(self, member: Member, database: ClanMembershipDatabase, **kwargs):
        super().__init__(**kwargs)
        self.clan_database = database
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
        self.clan_database.add_object(new_status)
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
        self._notes: Optional[TextArea] = None

    def add_field(self, title: str, /, id: str, disabled: bool = False, **kwargs):
        field = EscapableInput(id=id, disabled=disabled, **kwargs)
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
                    yield self.add_field(
                        "Discord Username",
                        id="discord_name",
                        validators=[
                            Length(minimum=1)
                        ]
                    )
                    yield self.add_field("Bungie Membership Number", id="bungie_id", disabled=True)
                    yield self.add_field("Date joined", id="joined")

                self._notes = TextArea(text=require_else(self._member.notes, ""), id="member_notes")
                self._notes.border_title = "Member Notes"
                yield self._notes

            with Grid(id="hist_n_accounts"):
                self.history_table = MemberHistoryTable(self._member, self._clan_database)
                yield self.history_table
                self.accounts_table = MemberAccountsTable(self._member, self._clan_database)
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

        self._member.notes = self._notes.text

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

    def __init__(self, clan_database: ClanMembershipDatabase, clan: Clan):
        super().__init__()
        self._clan = clan
        self._clan_database = clan_database
        self._unknown_table: Optional[UnknownPlayersTable] = None
        self._members_table: Optional[MembersTable] = None
        self._past_members_table: Optional[MembersTable] = None

        self._labels: Dict[str, Label] = {}

    def _add_label(self, name: str, content: str) -> Label:
        label = Label(content)
        self._labels[name] = label
        return label

    def compose(self) -> ComposeResult:
        yield Header()
        with Grid(id="list"):
            with Vertical(classes="area"):
                yield self._add_label("unknown", "Unknown Players from Bungie Clan")
                self._unknown_table = UnknownPlayersTable(self._clan_database, name="unknown_players")
                yield self._unknown_table
            with Vertical(classes="area"):
                yield self._add_label("current", "Current Members")
                self._members_table = MembersTable(membership_database=self._clan_database, name="current_members")
                yield self._members_table
            with Vertical(classes="area"):
                yield self._add_label("past", "Past Members")
                self._past_members_table = PastMembersTable(membership_database=self._clan_database,
                                                            name="past_members")
                yield self._past_members_table
        yield Footer()

    def on_mount(self) -> None:
        log.info("Updating tables")
        self._update_all()

    def _update_all(self):
        self._unknown_table.update(unknown_players := find_unknown_players(self._clan_database, self._clan))
        self._labels["unknown"].update(f"Unknown Players from Bungie Clan ({len(unknown_players)})")

        self._members_table.update(current := list(self._clan_database.current_members()))
        self._labels["current"].update(f"Current Members ({len(current)})")

        self._past_members_table.update(past := list(self._clan_database.past_members()))
        self._labels["past"].update(f"Past Members ({len(past)})")


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
