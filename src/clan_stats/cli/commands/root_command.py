import sys
from argparse import ArgumentParser

from . import version
from .clan_command import ClanCommand
from .command import Command
from .player_command import PlayerCommand
from .test_command import TestCommand
from .version import VersionCommand
from ...config import ClanStatsConfig


class RootCommand(Command):
    name = "constellation"
    help = "A tool to manage constellations of nebulae sandboxes."
    subcommands = [ClanCommand(), VersionCommand(), TestCommand(), PlayerCommand()]

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        parser.add_argument(
            "--version",
            action='store_true',
            help="Print version information and exit")

    def execute(self, args, config):
        if args.version:
            version.print_version()
        else:
            args.parser.print_usage(file=sys.stderr)
