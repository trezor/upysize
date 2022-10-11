from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import all_nodes, get_function_name


@dataclass
class Kwarg(SpaceSaving):
    name: str
    amount: int
    line_no: int

    def saved_bytes(self) -> int:
        """
        The cost of passing a keyword argument is 3 bytes,
        because it needs to LOAD a QSTR with the key, which costs exactly that.
        """
        return self.amount * 3

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.line_no} :: {self.name} ({self.amount}x) ({self.saved_bytes()} bytes)"


def keyword_arguments(
    file_content: str, settings: Settings = Settings()
) -> list[Kwarg]:
    """Looking for usages of keyword arguments in function calls.

    It may be then beneficial to replace them with positional arguments.
    """

    def iterator() -> Iterator[Kwarg]:
        for node in all_nodes(file_content):
            if isinstance(node, ast.Call):
                if node.keywords:
                    yield Kwarg(
                        name=get_function_name(node),
                        amount=len(node.keywords),
                        line_no=node.lineno,
                    )

    return sorted(list(iterator()), key=lambda x: x.line_no)
