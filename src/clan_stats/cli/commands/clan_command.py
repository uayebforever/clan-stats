import argparse
from argparse import ArgumentParser

from clan_stats import discord
from clan_stats.actions import activity_check, clan_fireteams, clan_events, raid_report
from clan_stats.config import ClanStatsConfig
from .command import Command
from ...data._bungie_api.bungie_enums import GameMode
from ...data.retrieval import get_default_data_retriever


class MemberActivitiesCommand(Command):
    name = "member-activities"
    help = "Get a list of clan members and their recent activity"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--discord-file", default=config.discord_destiny_mapping_file)
        parser.add_argument("--sort-by", choices=["name", "active", "discord"], default="name",
                            help="Whether to sort by name or most recently active")
        parser.add_argument("--activity-type", choices=["raid", "any"], default="name",
                            help="Filter by activity type")

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        discord_group = discord.group_from_csv_file(args.discord_file)
        activity_check.activity_summary(args.clan_id,
                                        discord_group,
                                        get_default_data_retriever(config),
                                        sort_by=args.sort_by,
                                        activity_mode=(GameMode.RAID
                                                       if args.activity_type == "raid"
                                                       else GameMode.NONE))


class ClanEventsCommand(Command):
    name = "clan-events"
    help = "List recent clan events"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        add_fireteam_finder_arguments(parser)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        clan_events.recent_clan_events(args.clan_id,
                                       get_default_data_retriever(config),
                                       recency_days=args.past_days,
                                       min_clan_fireteam_members=args.min_clanmates)


class RaidSummaryCommand(Command):
    name = "raid-summary"
    help = "Show clan raid clears"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--sort-by", choices=["name", "count"], default="name",
                            help="Whether to sort by name or most recently active")
        parser.add_argument("--discord-file", default=config.discord_destiny_mapping_file)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        discord_group = discord.group_from_csv_file(args.discord_file)
        raid_report.clears(args.clan_id, discord_group, get_default_data_retriever(config), args.sort_by)


class ClanFireteamsCommand(Command):
    name = "clan-fireteams"
    help = "List recent clan fireteams and their members"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        add_fireteam_finder_arguments(parser)

    def execute(self, args: argparse.Namespace, config: ClanStatsConfig) -> None:
        clan_fireteams.recent_clan_fireteams_summary(get_default_data_retriever(config),
                                                     args.clan_id,
                                                     recency_days=args.past_days,
                                                     min_clan_fireteam_members=args.min_clanmates)


class ClanCommand(Command):
    name = "clan"
    help = "Operations on a whole clan"
    subcommands = [MemberActivitiesCommand(), ClanFireteamsCommand(), ClanEventsCommand(), RaidSummaryCommand()]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("--clan-id", default=config.default_clan_id)


def add_fireteam_finder_arguments(parser: ArgumentParser) -> None:
    parser.add_argument("--min-clanmates",
                        default=2,
                        type=int,
                        help="Number of fireteam members from the clan to be considered a clan fireteam.")
    parser.add_argument("--past-days",
                        default=30,
                        type=int,
                        help="How many days of activity history to search.")
