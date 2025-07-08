from clan_stats.data.retrieval.actvity_database import SimpleActivityDatabase
from clan_stats.util.itertools import only
from randomdata import random_activity


def test_activity_database_store_retrieve():
    base = dict()

    db = SimpleActivityDatabase(base)

    activity = random_activity()

    db.set(activity)

    raw = only(base.values())
    assert isinstance(raw, str)

    retrieved = db.get(int(activity.time_period.start.timestamp()))

    assert retrieved == activity

    assert db.get(only(db.keys())) == activity


