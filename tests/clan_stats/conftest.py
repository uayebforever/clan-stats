from pathlib import Path

import pytest

from clan_stats import config


@pytest.fixture(scope="session")
def clan_stats_config() -> config.ClanStatsConfig:
    return config.read_config()


@pytest.fixture(scope="session")
def bungie_api_key(clan_stats_config) -> str:
    return clan_stats_config.bungie_api_key
