from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_toplevel_nodes, get_method_names


@dataclass
class InitOnlyClass(SpaceSaving):
    name: str
    line_no: int

    def saved_bytes(self) -> int:
        # it depends...
        return 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name}"


def init_only_classes(
    file_content: str, settings: Settings = Settings()
) -> list[InitOnlyClass]:
    """Looking for small classes only with __init__ constructor.

    If these classes are used only to store data for a short time,
    it could be beneficial to use tuples instead.
    """

    def iterator() -> Iterator[InitOnlyClass]:
        for node in all_toplevel_nodes(file_content):
            if isinstance(node, ast.ClassDef):
                if get_method_names(node) == ["__init__"]:
                    yield InitOnlyClass(node.name, node.lineno)

    return sorted(list(iterator()), key=lambda x: x.line_no)
