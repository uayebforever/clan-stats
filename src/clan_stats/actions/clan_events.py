import asyncio
from collections import defaultdict
from datetime import timedelta, datetime, timezone
from typing import Sequence, Dict, List, Tuple

from clan_stats.data.manifest import Manifest
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.event.event_finder import find_events, Event
from clan_stats.event.fireteams import SharedFireteamFinder
from clan_stats.fireteams import Fireteam
from clan_stats.terminal import MessageType, term
from clan_stats.data.types.individuals import Player, MinimalPlayer
from clan_stats.util.time import format_time_period_weekday_and_time, TimePeriod


def recent_clan_events(clan_id: int,
                       data_retriever: DataRetriever,
                       recency_days: int = 30,
                       min_clan_fireteam_members: int = 3,
                       min_event_length: timedelta = timedelta(minutes=45)) -> None:
    recency_limit = datetime.now(timezone.utc) - timedelta(days=recency_days)

    shared_fireteams, players_in_range, manifest = asyncio.run(
        _get_data(data_retriever, clan_id, recency_limit, min_clan_fireteam_members))

    term.print(MessageType.SECTION, "Bungie Clan Members active in the time range:")
    for player in players_in_range:
        term.print_player_line(player)

    events: Sequence[Event] = find_events(shared_fireteams,
                                          min_length=min_event_length)

    all_participants: Dict[str, int] = defaultdict(lambda: 0)

    for event in events:
        event_time = format_time_period_weekday_and_time(TimePeriod.for_range(event.start(), event.end()))
        term.print(MessageType.SECTION, f"Event {event_time}:")

        term.print(MessageType.TEXT, "  including:")
        for activity in event.highlight_activities():
            term.print(MessageType.TEXT, "    " + manifest.get_activity_name(activity.director_activity_hash)
                       + f"   ({activity.time_period.length})")

        term.print(MessageType.TEXT, "Participants:")
        names = event.participants_names()
        term.print_columnar_list(names)
        for name in names:
            all_participants[name] += 1

    term.print(MessageType.SUMMARY, "Events: " + str(len(events)))

    term.print(MessageType.SECTION, "Participants in any event:")
    term.print_columnar_list([f"{k} ({v})" for k, v in all_participants.items()])


async def _get_data(data_retriever: DataRetriever,
                    clan_id: int,
                    recency_limit: datetime,
                    min_clan_fireteam_members: int
                    ) -> Tuple[Sequence[Fireteam], Sequence[MinimalPlayer], Manifest]:
    async with data_retriever:
        clan = await data_retriever.get_clan(clan_id)
        manifest = await data_retriever.get_manifest()
        players_in_range = list(p
                                for p in clan.players
                                if p.last_online > recency_limit)

        shared_fireteams: Sequence[Fireteam] = await SharedFireteamFinder(data_retriever).shared_fireteams(
            players_in_range,
            recency_limit=recency_limit,
            min_size=min_clan_fireteam_members)

    return shared_fireteams, players_in_range, manifest
