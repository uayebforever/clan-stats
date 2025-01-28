from typing import TypeVar, Optional

_T = TypeVar('_T')

def require_else(optional_value: Optional[_T], other: _T) -> _T:
    return optional_value if optional_value is not None else other