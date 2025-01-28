import os
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Dict, List, TypeVar, Sequence, Tuple, Iterable, Optional

import blessed
from tabulate import tabulate

from clan_stats.data.manifest import Manifest
from clan_stats.data.types.activities import ActivityWithPost
from clan_stats.data.types.individuals import Player, MinimalPlayer, GroupMinimalPlayer
from clan_stats.util.time import format_time_as_delta, format_time_delta


class Verbosity(Enum):
    NONE = 0
    SUMMARY = 1
    UNPROCESSED = 2
    RULE_STATUS = 3


class MessageType(Enum):
    SUMMARY = auto()
    SECTION = auto()
    TEXT = auto()
    ERROR = auto()


class _Terminal(object):

    def __init__(self):
        self._terminal: blessed.Terminal = blessed.Terminal(force_styling=True)
        self._blocked: bool = False
        self._buffer: Dict[MessageType, List[str]] = {i: [] for i in MessageType}

    def block(self):
        self._blocked = True

    def unblock(self):
        self._blocked = False

    def print_player_line(self,
                          player: MinimalPlayer,
                          discord_name=None,
                          last_active: Optional[datetime] = None,
                          index: Optional[int]=None):
        if not self._blocked:
            # last_seen = format_time_as_delta(player.last_on_destiny) if player.last_on_destiny else ""
            if isinstance(player, GroupMinimalPlayer) or last_active is not None:
                last = last_active if last_active is not None else player.last_online
                last_seen = format_time_delta(last - datetime.now(timezone.utc))
                if last_active is None:
                    last_seen += "*"
            else:
                last_seen = ""
            name = self._terminal.bold_white(f"{player.name}")
            index_str = f"{index: 2d}" if index is not None else ""
            if discord_name:
                name = name + " / " + f"@{discord_name}"
            message = f"  {index_str} {name:70}" + self._terminal.blue(f" {last_seen:22}") + self._terminal.bright_black(
                f" ({player.primary_membership.membership_id})")
            self._print(message)

    def print_activity_summary(self,
                               activity: ActivityWithPost,
                               manifest: Manifest,
                               teammates: List[MinimalPlayer],
                               clanmates: bool = None):
        if not self._blocked:
            activity_name = self._terminal.white(manifest.get_activity_name(activity.director_activity_hash))
            start = format_time_as_delta(activity.time_period.start)
            message = f"      {activity_name:50}" + self._terminal.blue(f" {start:22}")
            if clanmates:
                message += "*"
            message += ", ".join(p.name for p in activity.players)
            self._print(message)

    def format_timestamp(self, time: datetime) -> str:
        return time.isoformat()

    def warning(self, message: str):
        if not self._blocked:
            self._print(self._terminal.yellow("WARNING: " + message))

    def skip(self, lines=1):
        self._print(os.linesep * lines)

    def print(self, type: MessageType, message: str):
        if not self._blocked:
            if type == MessageType.SECTION:
                self.skip(1)
                self._print(self._terminal.white(message))
            elif type == MessageType.TEXT:
                self._print(self._terminal.grey(message))
            elif type == MessageType.SUMMARY:
                self.skip(2)
                self._print(self._terminal.red(message))
                self.skip()
            else:
                self._print(message)

    def print_table(self, headings: Sequence[str], table: Sequence[Sequence[str]]):
        print(tabulate(table, headers=headings))

    def print_columnar_list(self, str_list: Iterable[str]):
        if not self._blocked:
            for line_batch in _batch(sorted(str_list, key=lambda s: s.lower()), 3, pad=""):
                term.print(MessageType.TEXT, "   {:30s}   {:30s}  {:30s}".format(*line_batch))

    def _print(self, message):
        print(self._terminal.truncate(message), flush=True)

    def _write(self, message):
        print(self._terminal.truncate(message), end="", flush=True)

    def buffer(self, type: MessageType, message: str):
        self._buffer[type].append(message)

    def clear_bol(self):
        if not self._blocked:
            self._write(self._terminal.clear_bol + self._terminal.move_x(0))

    def clear_buffer(self, type: MessageType):
        if not self._blocked:
            self._clear_error_buffer()
            self._clear_buffer(type)

    def _clear_error_buffer(self):
        self._clear_buffer(MessageType.ERROR)

    def _clear_buffer(self, type):
        buffer = self._buffer[type]
        while len(buffer) > 0:
            self.print(type, buffer.pop(0))

    @contextmanager
    def status(self, message):
        if self._blocked:
            raise SystemExit("Multiple status context managers")
        self._write(message)
        self.block()
        try:
            yield
        finally:
            self.unblock()
            self.clear_bol()
            self.clear_buffer(MessageType.ERROR)


T = TypeVar('T')


def _batch(seq: Sequence[T], size: int, pad=None) -> Sequence[Tuple[T, T, T]]:
    for i in range(-(-len(seq) // size)):
        end = min(i * size + size, len(seq))
        if pad is not None and i * size + size > len(seq):
            extra = [pad] * (i * size + size - len(seq))
        else:
            extra = []

        yield list(seq[i * size: end]) + extra


term: _Terminal = _Terminal()
