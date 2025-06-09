import os
from enum import StrEnum
from pathlib import Path

from clan_stats.config import ClanStatsConfig
from .aiobungie_rest_data_retriever import AioBungieRestDataRetriever
from .bungio_data_retriever import BungioDataRetriever
from .cached_data_retriever import CachedDataRetriever
from .data_retriever import DataRetriever


def get_default_data_retriever(config: ClanStatsConfig) -> DataRetriever:
    # return AioBungieRestDataRetriever(config.bungie_api_key)
    # return CachedDataRetriever(
    #     delegate=AioBungieRestDataRetriever(config.bungie_api_key),
    #     database_directory=Path(".").joinpath("cache"))
    return BungioDataRetriever(config.bungie_api_key)


class DataRetrieverType(StrEnum):
    BUNGIO = "bungio"
    AIOBUNGIE_REST = "aiobungie_rest"


def get_data_retriever(retriever: DataRetrieverType, config: ClanStatsConfig) -> DataRetriever:
    if retriever is DataRetrieverType.BUNGIO:
        return BungioDataRetriever(config.bungie_api_key)
    if retriever is DataRetrieverType.AIOBUNGIE_REST:
        return CachedDataRetriever(
            delegate=AioBungieRestDataRetriever(config.bungie_api_key),
            database_directory=Path(".").joinpath("cache"))
