from typing import TypeVar, Callable, Generic, Sequence, Self

from pydantic import BaseModel
from tabulate import tabulate

_T = TypeVar("_T")


class _Column(BaseModel, Generic[_T]):
    name: str
    render_func: Callable[[_T], str]


class TableBuilder(Generic[_T]):

    def __init__(self):
        self.columns: list[_Column[_T]] = []

    def add_column(self, name: str = "") -> Callable[[Callable[[_T], str]], 'TableBuilder[_T]']:
        def decorator(function: Callable[[_T], str]) -> Self:
            column = _Column(
                name=name,
                render_func=function)
            self.columns.append(column)
            return self

        return decorator

    def build(self, source: Sequence[_T]) -> str:
        data = self._build_data_array(source)
        return tabulate(data,
                        headers=[c.name for c in self.columns],
                        tablefmt='plain')

    def build_indexed(self, source: Sequence[_T]) -> str:
        data = self._build_data_array(source)
        return tabulate(data,
                        headers=[c.name for c in self.columns],
                        tablefmt='plain',
                        showindex=range(1, len(source)+1))

    def _build_data_array(self, source: Sequence[_T]) -> Sequence[Sequence[str]]:
        data: list[list[str]] = []
        for row in source:
            rendered_row: list[str] = []
            for column in self.columns:
                rendered_row.append(column.render_func(row))
            data.append(rendered_row)
        return data
