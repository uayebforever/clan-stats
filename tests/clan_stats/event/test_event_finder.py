from datetime import datetime, timedelta, timezone

import pytest

from clan_stats.data._bungie_api.bungie_enums import GameMode
from clan_stats.data.types.activities import Activity
from clan_stats.event.event_finder import find_events
from clan_stats.fireteams import Fireteam
from clan_stats.util.itertools import first, rest, only
from clan_stats.util.time import TimePeriod


@pytest.fixture
def fireteams():
    return [
        Fireteam(
            activity=Activity(
                instance_id=14758768928,
                director_activity_hash=1078036603,
                time_period=TimePeriod(
                    start=datetime(2024, 5, 5, 16, 45, 12,
                                   tzinfo=timezone.utc),
                    length=timedelta(seconds=1850)),
                primary_mode=GameMode.PRIVATEMATCHESALL,
                modes=[GameMode.PRIVATEMATCHESALL]),
            member_names={
                'Borealis-ray#379', 'Ostrythe#4620', 'Percival#1540', 'THE BEAN MAN#4016'}),
        Fireteam(
            activity=Activity(
                instance_id=14759516389,
                director_activity_hash=910380154,
                time_period=TimePeriod(
                    start=datetime(2024, 5, 5, 17, 17, 34,
                                   tzinfo=timezone.utc),
                    length=timedelta(seconds=8992)),
                primary_mode=GameMode.RAID, modes=[GameMode.ALLPVE, GameMode.RAID]),
            member_names={
                'Borealis-ray#379', 'Percival#1540', 'EnergizedHunter#3914', 'THE BEAN MAN#4016'}),
        Fireteam(
            activity=Activity(
                instance_id=14759928064,
                director_activity_hash=313828469,
                time_period=TimePeriod(
                    start=datetime(2024, 5, 5, 20, 3, 52,
                                   tzinfo=timezone.utc),
                    length=timedelta(seconds=3957)),
                primary_mode=GameMode.DUNGEON, modes=[GameMode.ALLPVE, GameMode.DUNGEON]),
            member_names={
                'Borealis-ray#379', 'EnergizedHunter#3914', 'THE BEAN MAN#4016'}),
        Fireteam(
            activity=Activity(
                instance_id=14764904214,
                director_activity_hash=1078036603,
                time_period=TimePeriod(
                    start=datetime(2024, 5, 6, 23, 45, 37,
                                   tzinfo=timezone.utc),
                    length=timedelta(seconds=1850)),
                primary_mode=GameMode.PRIVATEMATCHESALL,
                modes=[GameMode.PRIVATEMATCHESALL]),
            member_names={
                'Borealis-ray#379', 'Ostrythe#4620', 'Error Code Baboon (Adept)#9243',
                'Error Code: Weasel(Adept)#4301'})
    ]

def test_fireteams(fireteams):
    fireteams = sorted(fireteams,
                       key=lambda f: f.activity_start())

    prev_fireteam = None
    for fireteam in fireteams:
        n_participants = len(fireteam.member_names)
        gap = fireteam.activity_start() - prev_fireteam.activity_end() if prev_fireteam else 0
        print(n_participants, fireteam.activity.time_period.length, gap)
        prev_fireteam = fireteam


def test_find_events_single_fireteam_event(fireteams):
    events = find_events([fireteams[1]])

    assert len(events) > 0
    assert only(events).fireteams[0] == fireteams[1]

def test_find_events_single_event_two_fireteams(fireteams):
    events = find_events(fireteams[0:2])

    assert len(events) > 0
    assert only(events).fireteams[0] == fireteams[0]
    assert only(events).fireteams[1] == fireteams[1]

def test_find_all_events(fireteams):
    events = find_events(fireteams)

    assert len(events) == 1
    assert events[0].start() == fireteams[0].activity_start()
    assert events[0].end() == fireteams[2].activity_end()