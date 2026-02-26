"""Application preferences (persisted to disk)."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

from ..core.units import Units
from .machine_profiles import TormachModel


@dataclass
class AppSettings:
    """User preferences, serialized to ~/.tormachcam/settings.json."""

    default_machine: str = TormachModel.PCNC_770.value
    default_units: str = Units.INCH.value
    last_open_dir: str = ""
    last_save_dir: str = ""

    @staticmethod
    def _path() -> Path:
        return Path.home() / ".tormachcam" / "settings.json"

    def save(self) -> None:
        p = self._path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2))

    @classmethod
    def load(cls) -> "AppSettings":
        p = cls._path()
        if p.exists():
            data = json.loads(p.read_text())
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()
