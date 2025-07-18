import json
from datetime import timedelta, datetime, timezone
from typing import Sequence
from unittest.mock import MagicMock, AsyncMock

import pytest
from pydantic import BaseModel

from randomdata import random_int, random_player, \
    random_character, random_clan, random_activity, random_post_activity
from clan_stats.data.retrieval.cached_data_retriever import TimeStampedDataMappingWrapper, TimeStampedData, \
    SerializedMapping, CachedDataRetriever, _get_with_cache, _pydantic_to_python, _python_to_pydantic
from clan_stats.data.retrieval.data_retriever import DataRetriever
from clan_stats.data.types.individuals import Player
from clan_stats.util import time
from clan_stats.util.itertools import only


class TestCached:

    @pytest.mark.asyncio
    async def test_get_with_cache(self):
        cache = TimeStampedDataMappingWrapper(dict())

        class Foo(BaseModel):
            value: str

        foo = Foo(value="a")
        mock_supplier = AsyncMock(return_value=foo)

        assert await _get_with_cache(cache, 1, time.TP_1h, Foo, mock_supplier) == foo
        assert await _get_with_cache(cache, 1, time.TP_1h, Foo, mock_supplier) == foo
        assert await _get_with_cache(cache, 1, time.TP_1h, Foo, mock_supplier) == foo

        assert mock_supplier.call_count == 1

    @pytest.mark.asyncio
    async def test_get_player_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        player = random_player()
        assert isinstance(player, Player)

        delegate.get_player = AsyncMock(return_value=player)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        assert await retriever.get_player(123) == player
        assert await retriever.get_player(123) == player
        assert await retriever.get_player(123) == player
        assert await retriever.get_player(123) == player

        delegate.get_player.assert_called_once_with(123)

    @pytest.mark.asyncio
    async def test_get_characters_for_player_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        player = random_player()

        characters = [random_character(player), random_character(player)]

        delegate.get_characters_for_player = AsyncMock(return_value=characters)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        assert await retriever.get_characters_for_player(player) == characters
        assert await retriever.get_characters_for_player(player) == characters
        assert await retriever.get_characters_for_player(player) == characters
        assert await retriever.get_characters_for_player(player) == characters

        delegate.get_characters_for_player.assert_called_once_with(player)

    @pytest.mark.asyncio
    async def test_get_clan_for_player_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        player = random_player()

        clan = random_clan()

        delegate.get_clan_for_player = AsyncMock(return_value=clan)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        assert await retriever.get_clan_for_player(player) == clan
        assert await retriever.get_clan_for_player(player) == clan
        assert await retriever.get_clan_for_player(player) == clan
        assert await retriever.get_clan_for_player(player) == clan
        assert await retriever.get_clan_for_player(player) == clan

        delegate.get_clan_for_player.assert_called_once_with(player)

    @pytest.mark.asyncio
    async def test_get_activities_for_player_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        player = random_player()

        activities = [random_activity(), random_activity(), random_activity()]

        delegate.get_activities_for_player = AsyncMock(return_value=activities)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        async with retriever:
            result = await retriever.get_activities_for_player(player)
            await retriever.get_activities_for_player(player)
            await retriever.get_activities_for_player(player)
            await retriever.get_activities_for_player(player)

        delegate.get_activities_for_player.assert_called_once_with(player, min_start_date=None)

        # TODO: assert result == activities

    @pytest.mark.asyncio
    async def test_get_post_for_activity_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        activity = random_activity()

        post = [random_post_activity()]

        delegate.get_post_for_activity = AsyncMock(return_value=post)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        assert await retriever.get_post_for_activity(activity) == post
        assert await retriever.get_post_for_activity(activity) == post
        assert await retriever.get_post_for_activity(activity) == post
        assert await retriever.get_post_for_activity(activity) == post

        delegate.get_post_for_activity.assert_called_once_with(activity)

    @pytest.mark.asyncio
    async def test_get_clan_caching(self, tmp_path):
        delegate: DataRetriever = MagicMock(spec=DataRetriever)

        clan_id = random_int()

        clan = [random_clan()]

        delegate.get_clan = AsyncMock(return_value=clan)

        retriever = CachedDataRetriever(delegate, database_directory=tmp_path)

        assert await retriever.get_clan(clan_id) == clan
        assert await retriever.get_clan(clan_id) == clan
        assert await retriever.get_clan(clan_id) == clan
        assert await retriever.get_clan(clan_id) == clan
        assert await retriever.get_clan(clan_id) == clan

        delegate.get_clan.assert_called_once_with(clan_id)


def test_serialised_mapping_popo():
    delegate = dict()

    wrapper = SerializedMapping(delegate)

    key = random_int()
    data = {"value": 23, "more": ["a", 2, "3"]}
    wrapper[key] = data

    assert only(delegate) == str(key)
    stored_value = only(delegate.values())
    assert isinstance(stored_value, str)

    retrieved = wrapper[key]

    assert retrieved == data


def test_pydantic_serialization():
    class Foo(BaseModel):
        value: int
        more: Sequence[str | int]

    original = Foo(value=23, more=["a", 2, "3"])
    pyobj = _pydantic_to_python(original)

    raw = json.loads(json.dumps(pyobj))

    new = _python_to_pydantic(raw, Foo)

    assert new == original


def test_pydantic_sequence_serialization():
    class Foo(BaseModel):
        value: int
        more: Sequence[str | int]

    original = [
        Foo(value=23, more=["a", 2, "3"]),
        Foo(value=32, more=["b", 4, "1"])
    ]
    pyobj = _pydantic_to_python(original)

    raw = json.loads(json.dumps(pyobj))

    new = _python_to_pydantic(raw, Foo)

    assert new == original


def test_timestamped_data_wrapper():
    delegate = dict()
    wrapper = TimeStampedDataMappingWrapper(delegate)

    key = random_int()
    data = {"value": 23, "more": ["a", 2, "3"]}
    wrapper[key] = data

    assert only(delegate) == key
    stored_value = only(delegate.values())
    assert isinstance(stored_value, dict)
    assert "timestamp" in stored_value
    assert "data" in stored_value

    retrieved = wrapper[key]

    assert isinstance(retrieved, TimeStampedData)
    assert retrieved.data == data
    now = time.now()
    assert now - timedelta(seconds=1) <= retrieved.timestamp <= now


def test_timestamped_data_wrapper_with_timestamp():
    delegate = dict()
    wrapper = TimeStampedDataMappingWrapper(delegate)

    key = random_int()
    data = {"value": 23, "more": ["a", 2, "3"]}
    timestamp = datetime.fromtimestamp(random_int(), timezone.utc)
    wrapper[key] = TimeStampedData(timestamp, data)

    assert only(delegate) == key
    stored_value = only(delegate.values())
    assert isinstance(stored_value, dict)
    assert "timestamp" in stored_value
    assert "data" in stored_value

    retrieved = wrapper[key]

    assert isinstance(retrieved, TimeStampedData)
    assert retrieved.data == data
    assert retrieved.timestamp == timestamp


