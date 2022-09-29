from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import CacheCandidate, get_global_attribute_lookups


@dataclass
class GlobalImportCache(SpaceSaving):
    cache_candidate: CacheCandidate

    def saved_bytes(self) -> int:
        return self.cache_candidate.amount

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.cache_candidate} (~{self.saved_bytes()} bytes)"


def global_import_cache(
    file_content: str, settings: Settings = Settings(), threshold: int = 3
) -> list[GlobalImportCache]:
    """Looking for possibilities of caching global import attribute lookups.

    It may be then beneficial to create a global cache/alias for the attribute.
    """

    def iterator() -> Iterator[GlobalImportCache]:
        for symbol, lookups in get_global_attribute_lookups(file_content).items():
            for attr, amount in lookups.items():
                if amount >= threshold:
                    yield GlobalImportCache(CacheCandidate(f"{symbol}.{attr}", amount))

    return list(iterator())
