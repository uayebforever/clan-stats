from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.exceptions import UserError
from clan_stats.util.itertools import only, is_empty


async def resolve_clan(clan: int | str, data_retriever: DataRetriever) -> int:
    if isinstance(clan, int):
        return clan
    elif isinstance(clan, str):
        minimal_clan_list = await data_retriever.find_clans(clan)

        if is_empty(minimal_clan_list):
            raise UserError(f"No clan found with the name '{clan}'")

        return only(minimal_clan_list).id

    raise ValueError(f"Clan identifier '{clan}' cannot be resolved.")
