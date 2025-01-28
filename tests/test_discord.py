import tempfile
from pathlib import Path
from typing import Generator

import pytest

from clan_stats import discord


def test_group_from_csv_file():
    lines = [
        " # Destiny, discord, ",
        "JohnDoe#1234,             .jon_doe,               10/24/2023",
        "CoolKid11#1714,         james_cameron,",
        r"Its Complicated\, Really#4851,     complicated,       "
    ]
    file = _write_to_temp_file(lines)
    result = discord.group_from_csv_file(Path(file))
    assert result.get_discord("CoolKid11#1714") == "james_cameron"
    assert result.get_discord("Its Complicated, Really#4851") == "complicated"
    with pytest.raises(ValueError):
        result.get_discord("JohnDoe#1234")
    with pytest.raises(ValueError):
        result.get_discord("# Destiny")


def _write_to_temp_file(lines) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", delete=False)
    for line in lines:
        f.write(line + "\n")
    return f.name
