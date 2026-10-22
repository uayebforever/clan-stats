from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_raw_as

from .exceptions import ConfigError

DEFAULT_CONFIG_FILE = Path("clan_stats_config.yaml")

from logging import getLogger

_logger = getLogger()

class ClanStatsConfig(BaseModel):
    bungie_api_key: str

    default_player_id: int
    default_clan_id: int

    discord_destiny_mapping_file: Path = Field(default=Path("clan_list.csv"))


def read_config(config_file: Path = DEFAULT_CONFIG_FILE) -> ClanStatsConfig:
    directory = Path.cwd().resolve()
    while directory.parent != Path("/"):
        if directory.joinpath(config_file).is_file():
            with open(directory.joinpath(config_file), "r") as yml:
                return parse_yaml_raw_as(ClanStatsConfig, yml.read())
        else:
            directory = directory.parent
    # raise ConfigError(f"Cannot find or read config file {config_file}.")
    _logger.error(f"Unable to find/read config file {config_file}")
    return ClanStatsConfig(
        bungie_api_key="",
        default_player_id=4611686018467284386,
        default_clan_id=881267,
    )
