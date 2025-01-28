from clan_stats.config import read_config
from clan_stats.data.retrieval import get_default_data_retriever


def test_get_manifest():

    config = read_config()

    retriever = get_default_data_retriever(config)
    retriever.get_manifest()