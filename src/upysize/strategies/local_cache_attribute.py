from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import (
    CacheCandidate,
    Function,
    all_functions,
    get_func_local_attribute_lookups,
    is_attr_modified,
    is_symbol_assigned,
)


@dataclass
class LocalCache(SpaceSaving):
    cache_candidate: CacheCandidate
    func: Function
    attribute_mutated: bool
    symbol_assigned: bool

    def saved_bytes(self) -> int:
        return self.cache_candidate.amount * 2

    def __repr__(self) -> str:  # pragma: no cover
        mutated_msg = " (WARNING: attr gets mutated)" if self.attribute_mutated else ""
        assigned_msg = (
            " (WARNING: symbol gets (re)assigned)" if self.symbol_assigned else ""
        )
        warnings = mutated_msg + assigned_msg
        return f"{self.func} - {self.cache_candidate} (~{self.saved_bytes()} bytes){warnings}"


def local_cache_attribute(
    file_content: str, settings: Settings = Settings(), threshold: int = 4
) -> list[LocalCache]:
    """Looking for possibilities of caching local attribute lookups.

    It may be then beneficial to create a local cache/alias for the attribute.
    """

    def iterator() -> Iterator[LocalCache]:
        for func in all_functions(file_content):
            attr_lookups = get_func_local_attribute_lookups(file_content, func.node)
            for obj_name, attrs in attr_lookups.items():
                for attr_name, amount in attrs.items():
                    if amount >= threshold:
                        yield LocalCache(
                            cache_candidate=CacheCandidate(
                                f"{obj_name}.{attr_name}", amount
                            ),
                            func=func,
                            attribute_mutated=is_attr_modified(
                                func.node, obj_name, attr_name
                            ),
                            symbol_assigned=is_symbol_assigned(func.node, obj_name),
                        )

    return sorted(list(iterator()), key=lambda x: x.func.line_no)
