import asyncio
from argparse import ArgumentParser

from clan_stats.config import ClanStatsConfig
from clan_stats.terminal import term, MessageType
from .command import Command
from ...actions import player_activity_summary, player_search
from ...data.retrieval import get_default_data_retriever


class PlayerActivityReportCommand(Command):
    name = "activity-report"
    help = "Get an activity report for this player"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--past-days",
                            default=30,
                            type=int,
                            help="How many days of activity history to search.")

    def execute(self, args, config: ClanStatsConfig):
        player_activity_summary.activity_summary(get_default_data_retriever(config),
                                                 args.player_id,
                                                 days=args.past_days)


class FindPlayerCommand(Command):
    name = "find"
    help = "Find players"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("identifier", help="Player id or search string")

    def execute(self, args, config: ClanStatsConfig) -> None:
        player_search.player_search(get_default_data_retriever(config), args.identifier)


class PlayerCommand(Command):
    name = "player"
    help = "Commands for individual players."

    subcommands = [PlayerActivityReportCommand(), FindPlayerCommand()]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--player-id",
                            default=config.default_player_id,
                            help="The player id of the Bungie User")
