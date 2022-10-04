from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_constants, all_toplevel_symbol_usages


@dataclass
class LocalConstant(SpaceSaving):
    name: str
    usages: int

    def saved_bytes(self) -> int:
        return 4

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.name} ({self.usages} x) (~{self.saved_bytes()} bytes)"


def local_only_constants(
    file_content: str, settings: Settings = Settings()
) -> list[LocalConstant]:
    """Looking for constants that are (likely) only used in a module itself.

    If really so (they are not imported from other modules), their name
    can be prefixed with underscore to save some flash space and RAM.

    (We are not checking if the constant is used in other modules,
    it is up to the user to find it out.)
    """

    def iterator() -> Iterator[LocalConstant]:
        usages = all_toplevel_symbol_usages(file_content)

        for const in all_constants(file_content):
            # Those with underscores are already fine
            if const.startswith("_"):
                continue

            # When the constant is used in current module, there is
            # a chance it is local-only
            if const in usages:
                yield LocalConstant(const, usages[const])

    return list(iterator())
