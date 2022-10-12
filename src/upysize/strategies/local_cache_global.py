from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    Function,
    all_function_imported_symbols,
    all_functions,
    all_global_symbols,
    get_used_func_symbols,
)


@dataclass
class LocalCacheGlobal(SpaceSaving):
    cache_candidate: CacheCandidate
    func: Function

    def saved_bytes(self) -> int:
        """
        Accessing global variable costs 3 bytes

        Caching a global variable costs 4 bytes
        (ACCESS the variable (3) + STORE the new var (1)).

        Accessing it then costs just 1 byte.
        """
        investment = 4

        one_use_before = 3
        one_use_after = 1
        one_use_profit = one_use_before - one_use_after

        return self.cache_candidate.amount * one_use_profit - investment

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.func} - {self.cache_candidate} (~{self.saved_bytes()} bytes)"


def local_cache_global(
    file_content: str, settings: Settings = Settings(), threshold: int = 5
) -> list[LocalCacheGlobal]:
    """Looking for frequent usages of global symbols in local scope.

    It may be then beneficial to create a local cache/alias for the global symbol.
    """

    def iterator() -> Iterator[LocalCacheGlobal]:
        global_symbols = all_global_symbols(file_content)

        for func in all_functions(file_content):
            imported_in_func = all_function_imported_symbols(func.node)
            used_in_func = get_used_func_symbols(func.node)
            for symbol in used_in_func:
                if symbol in global_symbols and symbol not in imported_in_func:
                    amount = used_in_func[symbol]
                    if amount >= threshold:
                        yield LocalCacheGlobal(CacheCandidate(symbol, amount), func)

    return sorted(list(iterator()), key=lambda x: x.func.line_no)
