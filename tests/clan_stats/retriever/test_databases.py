import pytest

from clan_stats.data.retrieval.databases import KeyValueDatabase
from randomdata import random_int, random_string


class TestKeyValueDatabase:

    @pytest.fixture
    def db(self, tmp_path):
        with KeyValueDatabase(tmp_path.joinpath(f"db_{random_int()}.gdbm")) as db:
            yield db

    def test_store_retrieve(self, db):
        value = random_string().encode()
        db[b"blah"] = value
        assert db[b"blah"] == value

    def test_delete(self, db):
        value = random_string()
        db["blah"] = value
        del db['blah']
        with pytest.raises(KeyError):
            db[b"blah"]

    def test_iter(self, db):
        db[b"1"] = b"one"
        db[b"2"] = b"two"

        assert set(db.keys()) == {b"1", b"2"}
        assert set(db.values()) == {b"one", b"two"}

    def test_empty(self, db):
        assert list(db) == []