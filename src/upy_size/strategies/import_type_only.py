from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_toplevel_symbol_usages, all_type_hint_usages


@dataclass
class TypeOnlyImport(SpaceSaving):
    symbol: str

    def saved_bytes(self) -> int:
        return 7

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.symbol} (~{self.saved_bytes()} bytes)"


def type_only_import(
    file_content: str, settings: Settings = Settings()
) -> list[TypeOnlyImport]:
    """Looking for imports of symbols that are only used as a type hint.

    It is better to include these in `if TYPE_CHECKING` branch to be
    explicit about their intent and to save flash space.
    """

    def iterator() -> Iterator[TypeOnlyImport]:
        type_usages = all_type_hint_usages(file_content)

        for symbol, usages in all_toplevel_symbol_usages(file_content).items():
            if symbol in type_usages and type_usages[symbol] == usages:
                yield TypeOnlyImport(symbol)

    return list(iterator())
