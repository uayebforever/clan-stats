import argparse
import asyncio
from argparse import ArgumentParser
from typing import final

from clan_stats.actions import activity_check, clan_fireteams, clan_events, raid_report, interactive_clan_list
from clan_stats.actions.search import clan_search
from clan_stats.config import ClanStatsConfig
from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.retrieval import get_data_retriever, DataRetrieverType
from clan_stats.util.optional import require_else

from .command import Command


# pyright: reportAny=false

def _discord_file_argument(parser: ArgumentParser, config: ClanStatsConfig) -> None:
    _ = parser.add_argument("--discord-file", default=config.discord_destiny_mapping_file)


@final
class MemberActivitiesCommand(Command):
    name = "member-activities"
    help = "Get a list of clan members and their recent activity"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        _discord_file_argument(parser, config)
        _ = parser.add_argument("--sort-by", choices=["name", "active", "discord"], default="name",
                                help="Whether to sort by name or most recently active")
        _ = parser.add_argument("--activity-type", choices=["raid", "any"], default="name",
                                help="Filter by activity type")

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        asyncio.run(
            activity_check.activity_summary(
                require_else(args.clan, args.clan_id),
                get_data_retriever(DataRetrieverType(args.backend), config),
                sort_by=args.sort_by,
                activity_mode=(GameMode.RAID
                               if args.activity_type == "raid"
                               else GameMode.NONE)))


@final
class InteractiveEditCommand(Command):
    name = "edit"
    help = "Edit clan list interactively"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        pass
        # _discord_file_argument(parser, config)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig):
        asyncio.run(
            interactive_clan_list.interactive_clan_list(
                require_else(args.clan, args.clan_id),
                get_data_retriever(DataRetrieverType(args.backend), config)))


@final
class ClanEventsCommand(Command):
    name = "clan-events"
    help = "List recent clan events"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        add_fireteam_finder_arguments(parser)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        asyncio.run(
            clan_events.recent_clan_events(
                require_else(args.clan, args.clan_id),
                get_data_retriever(DataRetrieverType(args.backend), config),
                recency_days=args.past_days,
                min_clan_fireteam_members=args.min_clanmates))


@final
class RaidSummaryCommand(Command):
    name = "raid-summary"
    help = "Show clan raid clears"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        _ = parser.add_argument("--sort-by", choices=["name", "count"], default="name",
                                help="Whether to sort by name or most recently active")
        _ = parser.add_argument("--interactive", "-i",
                                action='store_true',
                                dest="interactive",
                                help="Display the table interactively")

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        asyncio.run(
            raid_report.clears(
                require_else(args.clan, args.clan_id),
                get_data_retriever(DataRetrieverType(args.backend), config),
                args.sort_by,
                args.interactive))


@final
class ClanFireteamsCommand(Command):
    name = "clan-fireteams"
    help = "List recent clan fireteams and their members"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        add_fireteam_finder_arguments(parser)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        asyncio.run(
            clan_fireteams.recent_clan_fireteams_summary(
                get_data_retriever(DataRetrieverType(args.backend), config),
                require_else(args.clan, args.clan_id),
                recency_days=args.past_days,
                min_clan_fireteam_members=args.min_clanmates))


@final
class ClanSearchCommand(Command):
    name = "search"
    help = "Search for a clan"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        _ = parser.add_argument("query",
                                help="string to query for")

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig):
        asyncio.run(
            clan_search(
                get_data_retriever(DataRetrieverType(args.backend), config),
                args.query))


@final
class ClanCommand(Command):
    name = "clan"
    help = "Operations on a whole clan"
    subcommands = [
        MemberActivitiesCommand(),
        ClanFireteamsCommand(),
        ClanEventsCommand(),
        RaidSummaryCommand(),
        InteractiveEditCommand(),
        ClanSearchCommand()
    ]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        group = parser.add_mutually_exclusive_group()
        _ = group.add_argument("--clan-id",
                               type=int,
                               default=config.default_clan_id,
                               help="The numeric ID of the clan to operate on.")
        _ = group.add_argument("--clan",
                               type=str,
                               help="The name of the clan to operate on.")


def add_fireteam_finder_arguments(parser: ArgumentParser) -> None:
    _ = parser.add_argument("--min-clanmates",
                            default=2,
                            type=int,
                            help="Number of fireteam members from the clan to be considered a clan fireteam.")
    _ = parser.add_argument("--past-days",
                            default=30,
                            type=int,
                            help="How many days of activity history to search.")
