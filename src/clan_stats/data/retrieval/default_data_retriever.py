from enum import StrEnum

from clan_stats.config import ClanStatsConfig
from clan_stats.exceptions import ApplicationError

from .bungio_data_retriever import BungioDataRetriever
from .data_retriever import DataRetriever


def get_default_data_retriever(config: ClanStatsConfig) -> DataRetriever:
    return BungioDataRetriever(config.bungie_api_key)


class DataRetrieverType(StrEnum):
    BUNGIO = "bungio"
    AIOBUNGIE_REST = "aiobungie_rest"


def get_data_retriever(retriever: DataRetrieverType, config: ClanStatsConfig) -> DataRetriever:
    if retriever is DataRetrieverType.BUNGIO:
        return BungioDataRetriever(config.bungie_api_key)
    else:
        raise ApplicationError(f"Unknown data retriever: {retriever}")
