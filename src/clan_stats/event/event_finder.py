from dataclasses import dataclass
from datetime import timedelta, datetime
from typing import Sequence, List, Iterable, Set, Iterator

from clan_stats.data.types.activities import Activity
from clan_stats.fireteams import Fireteam
from clan_stats.util.time import TP_1h


@dataclass
class Event:
    fireteams: List[Fireteam]

    def start(self):

        return min(map(_activity_start_time, self.activities()))

    def end(self):
        return max(map(_activity_end_time, self.activities()))

    def length(self) -> timedelta:
        return self.end() - self.start()

    def activities(self) -> List[Activity]:
        return [f.activity for f in self.fireteams]

    def add(self, fireteam: Fireteam):
        self.fireteams.append(fireteam)

    def highlight_activities(self) -> List[Activity]:
        highlights = list()
        for activity in sorted(self.activities(), key=Activity.length, reverse=True):
            if len(highlights) < 1 or activity.time_period.length > timedelta(minutes=45):
                highlights.append(activity)
            if len(highlights) > 2:
                break
        return highlights

    def participants_names(self) -> Iterable[str]:
        participants: Set[str] = set()
        for fireteam in self.fireteams:
            participants.update(fireteam.member_names)
        return participants

def _activity_start_time(a: Activity) -> datetime:
    return a.time_period.start

def _activity_end_time(a: Activity) -> datetime:
    return a.time_period.end

def find_events(fireteams: Iterable[Fireteam],
                max_gap: timedelta = TP_1h,
                min_length: timedelta = timedelta(minutes=45)) -> Sequence[Event]:
    sorted_fireteams = list(sorted(fireteams, key=lambda f: f.activity_start()))

    prev_fireteam = sorted_fireteams[0]

    result: List[Event] = [Event(fireteams=[prev_fireteam])]

    for fireteam in sorted_fireteams[1:]:
        if fireteam.activity_start() - prev_fireteam.activity_end() < max_gap:
            result[-1].add(fireteam)
        else:
            result.append(Event(fireteams=[fireteam]))
        prev_fireteam = fireteam

    return list(e for e in result if e.length() > min_length)
