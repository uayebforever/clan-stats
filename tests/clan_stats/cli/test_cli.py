from clan_stats.cli.cli_main import _parse_args
from clan_stats.config import ClanStatsConfig

CONFIG = ClanStatsConfig(bungie_api_key="dummy", default_player_id=1, default_clan_id=2)


def test_activity_report_filters():
    args = _parse_args(["player", "activity-report", "--filter", "raid:LW", "--filter", "dungeon"], CONFIG)

    assert args.filter == ["raid:LW", "dungeon"]


def test_activity_report_without_filter():
    args = _parse_args(["player", "activity-report"], CONFIG)

    assert args.filter is None


def test_activities_list():
    args = _parse_args(["activities", "list", "raid", "--search", "wish", "--hashes"], CONFIG)

    assert (args.type, args.search, args.hashes) == ("raid", "wish", True)


def test_activities_types():
    args = _parse_args(["activities", "types"], CONFIG)

    assert args.command_executable is not None
