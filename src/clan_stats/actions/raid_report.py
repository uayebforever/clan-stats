import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum
from typing import Tuple, Mapping, Sequence, Optional

from math import log10, floor
from textual import events
from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.widgets import Header, DataTable, Footer

from aiobungie import GameMode
from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.activities import Activity
from clan_stats.data.types.clan import Clan
from clan_stats.data.types.individuals import MinimalPlayer
from clan_stats.terminal import term
from clan_stats.util.async_utils import collect_map


def clears(clan_id: int, data_retriever: DataRetriever, sort_by: str = "name", interactive=False):
    clan, raid_data, manifest = asyncio.run(_fetch_clan_raid_data(data_retriever, clan_id))

    raid_counts = {player_name: _raid_counts(raids, manifest) for player_name, raids in raid_data.items()}

    if sort_by == "name":
        def sort_key(i: Tuple[str, Mapping[Raid, int]]):
            return i[0].lower()
    elif sort_by == "count":
        def sort_key(i: Tuple[str, Mapping[Raid, int]]):
            return sum(i[1].values()) if i[1] is not None else 0
    else:
        raise KeyError(f"Invalid sort by '{sort_by}'")

    tabulated_counts = format_table_cells([
        ([p] + [counts[r] for r in Raid.current_raids()] + [sum(counts.values())]
         if counts
         else [p] + ["-" for r in Raid.current_raids()] + ["-"])
        for p, counts in sorted(raid_counts.items(), key=sort_key)
    ])
    headings = [""] + [r.name for r in Raid.current_raids()] + ["Total"]

    if not interactive:
        term.print_table(headings, tabulated_counts)
    else:
        RaidReport(headings, tabulated_counts).run(loop=asyncio.new_event_loop())


class Raid(StrEnum):
    SE = "Salvation's Edge"
    CROTA = "Crota's End"
    ROOT = "Root of Nightmares"
    KF = "King's Fall"
    VOW = "Vow of the Disciple"
    VOG = "Vault of Glass"
    DSC = "Deep Stone Crypt"
    GOS = "Garden of Salvation"
    LW = "Last Wish"
    LEV = "Leviathan"
    PAN = "Pantheon"
    COS = "Crown of Sorrow"
    SOTP = "Scourge of the Past"
    UNKNOWN = "Unknown?"

    @classmethod
    def current_raids(cls) -> Sequence['Raid']:
        return [cls.SE, cls.CROTA, cls.ROOT, cls.KF, cls.VOW, cls.VOG, cls.DSC, cls.GOS, cls.LW]

    @classmethod
    def from_director_activity_hash(cls, dah: int, manifest: Manifest) -> 'Raid':
        activity_name = manifest.get_activity_name(dah)
        for raid in cls.__members__.values():
            if raid.value in activity_name:
                return raid
            elif dah in (4103176774,):
                return cls.UNKNOWN
        raise KeyError(f"Unknown raid hash {dah} mapping to {activity_name}")


async def _fetch_clan_raid_data(
        data_retriever: DataRetriever,
        clan_id: int
) -> Tuple[Clan, Mapping[str, Optional[Sequence[Activity]]], Manifest]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        raid_data = await _get_raids(data_retriever, clan.players)
        manifest = await data_retriever.get_manifest()

    return clan, raid_data, manifest


async def _get_raids(data_retriever: DataRetriever,
                     players: Sequence[MinimalPlayer]
                     ) -> Mapping[str, Optional[Sequence[Activity]]]:
    player_raids = await collect_map(
        {p.name: data_retriever.get_activities_for_player(
            p, mode=GameMode.RAID, min_start_date=datetime(year=2022, month=1, day=1, tzinfo=timezone.utc))
            for p in players})
    return player_raids


def _raid_counts(raids: Optional[Sequence[Activity]],
                 manifest: Optional[Manifest] = None
                 ) -> Optional[Mapping[Raid, int]]:
    result = defaultdict(lambda: 0)

    if raids is None:
        return None

    for activity in raids:
        raid = Raid.from_director_activity_hash(activity.director_activity_hash, manifest)
        if activity.completed is True:
            result[raid] += 1

    return result


class RaidReport(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "sort", "Sort table by current column")
    ]

    def __init__(self, headings: Sequence[str], raid_data: Sequence[Sequence[str]]):
        super().__init__()
        self._headings = headings
        self._raid_data = raid_data
        self._last_sort = ""
        self._last_row: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        self._populate_data_table(table)
        table.cursor_type = 'row'

    def on_key(self, event: events.Key) -> None:
        key = event.key
        table = self.query_one(DataTable)
        if table.cursor_type == 'row' and key == 'right':
            self._save_row()
            table.cursor_type = 'column'
        if table.cursor_type == 'column' and key == 'left' and table.cursor_column == 1:
            table.cursor_type = 'row'
            self._restore_row()
        if table.cursor_type == 'column' and (key == 'up' or key == 'down'):
            table.cursor_type = 'row'
            self._restore_row()
            event.prevent_default()

    def action_sort(self):
        table = self.query_one(DataTable)
        if table.cursor_type != 'row':
            column_key = table.coordinate_to_cell_key(table.cursor_coordinate).column_key
        else:
            self._save_row()
            column_key = table.coordinate_to_cell_key(Coordinate(0, 0)).column_key
        table.sort(column_key,
                   key=data_table_sort_case_insensitive,
                   reverse=column_key == self._last_sort)
        self._last_sort = column_key if column_key != self._last_sort else ""
        if table.cursor_type == 'row':
            self._restore_row()

    def _save_row(self):
        table = self.query_one(DataTable)
        self._last_row = table.coordinate_to_cell_key(table.cursor_coordinate).row_key

    def _restore_row(self):
        table = self.query_one(DataTable)
        cursor = table.get_cell_coordinate(self._last_row, "")
        table.move_cursor(row=cursor.row, column=cursor.column)

    def action_quit(self) -> None:
        table = self.query_one(DataTable)
        self.exit(return_code=0)

    def _populate_data_table(self, table: DataTable):
        for column_name in self._headings:
            table.add_column(column_name, key=column_name)

        for row in self._raid_data:
            table.add_row(*row,
                          key=row[0])


def data_table_sort_case_insensitive(*args):
    result = []
    for arg in args:
        if isinstance(arg, str):
            result.append(arg.lower())
        else:
            result.append(arg)
    return result


def format_table_cells(table: Sequence[Sequence[str | int]]) -> Sequence[Sequence[str]]:
    if len(table) == 0:
        return []

    max_values = [0 for _ in table[0]]
    for row in table:
        for i, cell in enumerate(row):
            if isinstance(cell, int):
                max_values[i] = max(max_values[i], cell)

    max_digits = [floor(log10(m)) + 1 if m > 1 else 1 for m in max_values]
    formatted_table = []
    for row in table:
        formated_row = []
        for i, cell in enumerate(row):
            if isinstance(cell, int):
                formated_row.append(format(cell, f"{max_digits[i]}d"))
            elif isinstance(cell, str):
                if max_digits[i] > 0:
                    formated_row.append(format(cell, f">{max_digits[i]}s"))
                else:
                    formated_row.append(cell)
            else:
                formated_row.append(str(cell))
        formatted_table.append(formated_row)
    return formatted_table
