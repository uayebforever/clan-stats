from pathlib import Path

from pydantic import BaseModel, Field
from pydantic_yaml import parse_yaml_raw_as

from .exceptions import ConfigError

DEFAULT_CONFIG_FILE = Path("clan_stats_config.yaml")


class ClanStatsConfig(BaseModel):
    bungie_api_key: str

    default_player_id: int
    default_clan_id: int

    discord_destiny_mapping_file: Path = Field(default=Path("clan_list.csv"))


def read_config(config_file: Path = DEFAULT_CONFIG_FILE):
    directory = Path.cwd().resolve()
    while directory.parent != Path("/"):
        if directory.joinpath(config_file).is_file():
            with open(directory.joinpath(config_file), "r") as yml:
                return parse_yaml_raw_as(ClanStatsConfig, yml.read())
        else:
            directory = directory.parent
    raise ConfigError(f"Cannot find or read config file {config_file}.")
