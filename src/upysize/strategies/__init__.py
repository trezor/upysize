from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class SpaceSaving(Protocol):
    def saved_bytes(self) -> int:  # pragma: no cover
        ...


@dataclass
class Settings:
    file_path: Path = Path(".")
    not_inlineable_funcs: list[str] = field(default_factory=list)
