import functools

import blessed
import pytest

from clan_stats.terminal_ui.message import message_of
from clan_stats.terminal_ui.terminal_formatter import TerminalFormatter


class TestTerminalFormatter:

    @pytest.fixture
    def formatter(self) -> TerminalFormatter:
        class MockTerminal(blessed.Terminal):
            @property
            def width(self):
                return 40

        return TerminalFormatter(lambda s: f"_{s}_", MockTerminal())

    def test_format_token(self, formatter: TerminalFormatter):
        result = formatter.format_token("Guardian")

        assert result == "_Guardian_"

    def test_format_message_with_plain_tokens(self, formatter: TerminalFormatter):
        result = formatter.format_message(
            message_of("Hi {0}!", "Guardian")
        )

        assert result == "Hi _Guardian_!"

    def test_format_message_with_named_tokens(self, formatter: TerminalFormatter):
        result = formatter.format_message(
            message_of("Hi {you}, say hello to {other}!", you="Guardian", other="Zavala")
        )

        assert result == "Hi _Guardian_, say hello to _Zavala_!"

    def test_format_different_types(self):
        @functools.singledispatch
        def format_token(a) -> str:
            return str(a)

        @format_token.register
        def _(a: int) -> str:
            return f"(int) {a}"

        @format_token.register
        def _(a: float) -> str:
            return f"(float) {a:0.2f}"


        result = TerminalFormatter(format_token).format_message(
            message_of("{name} has a {num1} and a {num2}", name="Zavala", num1=12, num2=1.234)
        )

        assert result == "Zavala has a (int) 12 and a (float) 1.23"

    def test_format_list_in_columns(self, formatter: TerminalFormatter):
        result = formatter.format_list_in_columns(sorted(
            ["James", "Paul", "Zavala", "Ikora", "Mara Sov"]))

        assert result[0] == "_Ikora_     _Mara Sov_  _Zavala_  "
        assert result[1] == "_James_     _Paul_                "

        # Because we fill down first, and then across, we may not fill all the columns. 
        result = formatter.format_list_in_columns(sorted(
            ["James", "Paul", "Ikora", "Mara Sov"]))

        assert result[0] == "_Ikora_     _Mara Sov_"
        assert result[1] == "_James_     _Paul_    "


