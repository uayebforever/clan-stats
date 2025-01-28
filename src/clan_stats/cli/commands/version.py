from argparse import ArgumentParser

from clan_stats import __version__ as package_version
from .command import Command
from ...config import ClanStatsConfig


class VersionCommand(Command):
    name = "version"
    help = "Print version information"

    def configure_arg_parser(self, parser: ArgumentParser, config: ClanStatsConfig) -> None:
        # No arguments
        pass

    def execute(self, args, config):
        print_version()


def print_version():
    print(f"clan_stats version: {package_version}")
