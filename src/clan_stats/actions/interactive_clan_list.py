import asyncio
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.widgets import Welcome, DataTable, Header, Footer

from clan_stats import discord
from clan_stats.discord import DiscordGroup, DiscordMember
from clan_stats.util.optional import require_else


class InteractiveClanList:

    def __init__(self, discord_csv_file: Path):
        self._discord_csv_file = discord_csv_file
        self._discord: Optional[DiscordGroup] = None

    def run(self):
        edit_app = EditApp(discord.group_from_csv_file(self._discord_csv_file))
        edit_app.run()


class EditApp(App):
    def __init__(self, discord_group: DiscordGroup):
        super().__init__()
        self._discord_group = discord_group

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable()
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        self._populate_data_table(table)


    def _populate_data_table(self, table: DataTable):
        for field_id, field in DiscordMember.model_fields.items():
            table.add_column(require_else(field.title, field_id))

        for member in self._discord_group.members:

            table.add_row(*(getattr(member, field) for field in DiscordMember.model_fields),
                          key=member.charlemagne_name)
