from typing import TypeVar, Optional, Callable

_T = TypeVar('_T')
_R = TypeVar('_R')


def require_else(optional_value: Optional[_T], other: _T) -> _T:
    return optional_value if optional_value is not None else other


def map_optional(optional_value: Optional[_T], function: Callable[[_T], _R]):
    return function(optional_value) if optional_value is not None else None
