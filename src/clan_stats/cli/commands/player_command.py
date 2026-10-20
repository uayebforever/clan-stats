import asyncio
from argparse import ArgumentParser
from typing import final

from clan_stats.actions import player_activity_summary, search
from clan_stats.config import ClanStatsConfig
from clan_stats.data.retrieval import get_data_retriever, DataRetrieverType
from .command import Command


@final
class PlayerActivityReportCommand(Command):
    name = "activity-report"
    help = "Get an activity report for this player"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--past-days",
                            default=30,
                            type=int,
                            help="How many days of activity history to search.")
        parser.add_argument("--filter",
                            action="append",
                            metavar="TYPE[:ACTIVITY[:VARIANT]]",
                            help="Only show matching activities, e.g. 'raid', 'raid:LW' or 'raid:VotD:master'. "
                                 "Activities and variants match by name, initials or a unique part of the name. "
                                 "Repeat to include several. See 'clan-stats activities' for valid values.")

    def execute(self, args, config: ClanStatsConfig):
        player_activity_summary.activity_summary(get_data_retriever(DataRetrieverType(args.backend), config),
                                                 args.player_id,
                                                 days=args.past_days,
                                                 filters=args.filter)


@final
class FindPlayerCommand(Command):
    name = "find"
    help = "Find players"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("identifier", help="Player id or search string")

    def execute(self, args, config: ClanStatsConfig) -> None:
        asyncio.run(
            search.trials_report_player_search(
                get_data_retriever(DataRetrieverType(args.backend), config),
                args.identifier))


class PlayerCommand(Command):
    name = "player"
    help = "Commands for individual players."

    subcommands = [PlayerActivityReportCommand(), FindPlayerCommand()]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--player-id",
                            default=config.default_player_id,
                            help="The player id of the Bungie User")
