import dbm.gnu
from pathlib import Path
from types import TracebackType
from typing import MutableMapping, ContextManager, Self, Type


class KeyValueDatabase(MutableMapping[bytes, bytes], ContextManager):

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self.db = None

    def __enter__(self) -> Self:
        self.db = dbm.gnu.open(str(self._db_path), "c")
        self.db.__enter__()
        return self

    def __exit__(self,
                 exception_type: Type[BaseException] | None,
                 exception: BaseException | None,
                 traceback: TracebackType | None) -> bool | None:
        self.db.__exit__(exception_type, exception, traceback)
        return False

    def __setitem__(self, __key: str, __value: str):
        self.db.__setitem__(__key, __value)

    def __delitem__(self, __key):
        self.db.__delitem__(__key)

    def __getitem__(self, __key) -> str:
        value = self.db.__getitem__(__key)
        if value is None:
            raise KeyError
        return value

    def __len__(self):
        n = 0
        last_key = self.db.firstkey()
        while last_key is not None:
            n += 1
            last_key = self.db.nextkey(last_key)
        return n

    def __iter__(self):
        last_key = self.db.firstkey()
        while last_key is not None:
            yield last_key
            last_key = self.db.nextkey(last_key)
