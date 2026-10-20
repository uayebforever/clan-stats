from argparse import ArgumentParser
from typing import final

from clan_stats.actions import activity_list
from clan_stats.config import ClanStatsConfig
from clan_stats.data.retrieval import get_data_retriever, DataRetrieverType
from .command import Command


@final
class ActivityTypesCommand(Command):
    name = "types"
    help = "List activity types usable in activity filters"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        pass

    def execute(self, args, config: ClanStatsConfig):
        activity_list.list_types(get_data_retriever(DataRetrieverType(args.backend), config))


@final
class ActivityListCommand(Command):
    name = "list"
    help = "List activities and their variants usable in activity filters"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument("type", nargs="?", help="Only list activities of this type, e.g. 'raid'")
        parser.add_argument("--search", help="Only list activities matching this name, initials or part of a name")
        parser.add_argument("--hashes", action="store_true", help="Show the activity hashes of each activity")

    def execute(self, args, config: ClanStatsConfig):
        activity_list.list_activities(get_data_retriever(DataRetrieverType(args.backend), config),
                                      type_text=args.type,
                                      search=args.search,
                                      show_hashes=args.hashes)


class ActivitiesCommand(Command):
    name = "activities"
    help = "List the activity types and activities known to the Destiny manifest."

    subcommands = [ActivityTypesCommand(), ActivityListCommand()]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        pass
