import asyncio
from typing import Optional

from clan_stats.data.activity_catalog import ActivityCatalog, initials, mode_name
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.terminal import term


def list_types(data_retriever: DataRetriever):
    catalog = asyncio.run(_get_catalog(data_retriever))
    term.print_table(["TYPE", "ACTIVITIES"],
                     [[mode_name(mode), str(len(catalog.activities(mode)))] for mode in catalog.types()])


def list_activities(data_retriever: DataRetriever,
                    type_text: Optional[str] = None,
                    search: Optional[str] = None,
                    show_hashes: bool = False):
    catalog = asyncio.run(_get_catalog(data_retriever))
    modes = [catalog.resolve_type(type_text)] if type_text else catalog.types()
    activities = (catalog.search(search, modes) if search
                  else [a for mode in modes for a in catalog.activities(mode)])

    headings = ["TYPE", "ACTIVITY", "INITIALS", "VARIANTS"] + (["HASHES"] if show_hashes else [])
    rows = []
    for activity in activities:
        row = [mode_name(activity.mode), activity.name, initials(activity.name).upper(),
               ", ".join(activity.variants.keys())]
        if show_hashes:
            row.append(", ".join(str(h) for h in sorted(activity.hashes)))
        rows.append(row)
    term.print_table(headings, rows)


async def _get_catalog(data_retriever: DataRetriever) -> ActivityCatalog:
    async with data_retriever:
        manifest = await data_retriever.get_manifest()
    return ActivityCatalog.from_manifest(manifest)
