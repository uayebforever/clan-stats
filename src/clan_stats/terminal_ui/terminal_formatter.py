from itertools import zip_longest, islice
from math import ceil
from typing import final, Callable, Any, Sequence, TypeVar, Iterator, Iterable
from logging import getLogger

import blessed

from clan_stats.terminal_ui.message import Message

log = getLogger(__name__)


@final
class TerminalFormatter:

    def __init__(self, token_formatter: Callable[[Any], str], terminal=blessed.Terminal()):
        self._format = token_formatter
        self._terminal = terminal

    def format_message(self, message: Message) -> str:
        formatted_tokens = [self._format(a) for a in message.tokens]
        named_formatted_tokens = {k: self._format(v) for k, v in message.named_tokens.items()}

        return message.message.format(*formatted_tokens, **named_formatted_tokens)

    def format_token(self, token: Any) -> str:
        return self._format(token)

    def format_list_in_columns(self, items: Sequence[Any], colsep="  ") -> Sequence[str]:
        width = self._terminal.width

        formatted_items = [self._format(i) for i in items]

        largest = max(map(self._terminal.length, formatted_items))

        n_max_columns = width // (largest + len(colsep))
        n_items = len(items)
        n_rows = ceil(n_items / n_max_columns)
        n_columns = ceil(n_items / n_rows)

        row_format = (("{:" + str(largest) + "}" + colsep) * n_columns).strip(" ")
        output: list[str] = []
        for row in zip_longest(*list(batched(formatted_items, n_rows)), fillvalue=""):
            output.append(row_format.format(*row))

        return output


_T = TypeVar("_T")


# Can be removed when we upgrade to Python 3.12
def batched(iterable: Iterable[_T], n: int) -> Iterator[Sequence[_T]]:
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError('n must be at least one')
    iterator = iter(iterable)
    while batch := tuple(islice(iterator, n)):
        yield batch
