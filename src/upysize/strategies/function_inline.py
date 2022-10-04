from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from . import Settings, SpaceSaving
from .helpers import Function, all_functions, get_function_call_amounts


@dataclass
class InlineFunction(SpaceSaving):
    func: Function

    def saved_bytes(self) -> int:
        return 50

    def __repr__(self) -> str:  # pragma: no cover
        return f"{self.func} (~ {self.saved_bytes()} bytes)"


def function_inline(
    file_content: str, settings: Settings = Settings()
) -> list[InlineFunction]:
    """Looking for one-time functions that can be possibly inlined.

    (We are not checking if those functions are not imported and used
    in some other module - it is up to user to check it.)

    To account for falsely reported functions, a list of functions
    can be specified in `settings.not_inlineable_funcs`, which will
    be ignored.
    """

    def iterator() -> Iterator[InlineFunction]:
        not_to_report = settings.not_inlineable_funcs
        function_calls = get_function_call_amounts(file_content)

        # Looking whether the function is called EXACTLY once in this file
        # (it indicates it MIGHT BE a one-time helper function)
        # (it might be used also elsewhere, but searching it would be quite hard)
        for func in all_functions(file_content):
            if func.name in not_to_report:
                continue

            if func.name in function_calls and function_calls[func.name] == 1:
                yield InlineFunction(func)

    return sorted(list(iterator()), key=lambda x: x.func.line_no)
