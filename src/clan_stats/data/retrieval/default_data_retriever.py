import os
from pathlib import Path

from clan_stats.config import ClanStatsConfig
from .aiobungie_rest_data_retriever import AioBungieRestDataRetriever
from .cached_data_retriever import CachedDataRetriever
from .data_retriever import DataRetriever


def get_default_data_retriever(config: ClanStatsConfig) -> DataRetriever:
    # return AioBungieRestDataRetriever(config.bungie_api_key)
    return CachedDataRetriever(
        delegate=AioBungieRestDataRetriever(config.bungie_api_key),
        database_directory=Path(".").joinpath("cache"))
