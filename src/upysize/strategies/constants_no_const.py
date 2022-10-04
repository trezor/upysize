from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_global_assignments, get_variable_name, is_a_constant_number_var


@dataclass
class NoConstNumber(SpaceSaving):
    name: str

    def saved_bytes(self) -> int:
        return 4

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name} (~{self.saved_bytes()} bytes)"


def no_const_number(
    file_content: str, settings: Settings = Settings()
) -> list[NoConstNumber]:
    """Looking for assignments of constant number variables without `const`.

    For these cases it may be beneficial to wrap them in `micropython.const`.
    """

    def iterator() -> Iterator[NoConstNumber]:
        for assignment in all_global_assignments(file_content):
            if is_a_constant_number_var(file_content, assignment):
                yield NoConstNumber(get_variable_name(assignment))

    return list(iterator())
