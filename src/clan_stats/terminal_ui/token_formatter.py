import functools
from typing import Any

import blessed

from clan_stats.terminal_ui.text_formatting import SectionHead

_term: blessed.Terminal = blessed.Terminal()

# Default/fall back formatter
@functools.singledispatch
def format_token(token: Any) -> str:
    return str(token)

@format_token.register
def _(token: SectionHead) -> str:
    return _term.white(token)

