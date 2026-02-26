"""Tormach PCNC 440 / 770 / 1100 machine profiles.

Travel limits are in inches (Tormach standard).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..gcode.validate import MachineEnvelope


@dataclass
class MachineProfile:
    """Specification for a specific Tormach mill model."""

    model: str
    x_travel: float   # inches
    y_travel: float
    z_travel: float
    min_rpm: int
    max_rpm: int
    max_feed_ipm: float
    envelope: MachineEnvelope

    def __str__(self) -> str:
        return (
            f"Tormach {self.model}  "
            f"X={self.x_travel}\" Y={self.y_travel}\" Z={self.z_travel}\"  "
            f"{self.min_rpm}–{self.max_rpm} RPM  "
            f"{self.max_feed_ipm} IPM"
        )


class TormachModel(Enum):
    PCNC_440 = "PCNC 440"
    PCNC_770 = "PCNC 770"
    PCNC_1100 = "PCNC 1100"


_PROFILES: dict[TormachModel, MachineProfile] = {
    TormachModel.PCNC_440: MachineProfile(
        model="PCNC 440",
        x_travel=10.0,
        y_travel=6.25,
        z_travel=10.0,
        min_rpm=100,
        max_rpm=10000,
        max_feed_ipm=110.0,
        envelope=MachineEnvelope(
            x_min=0.0, x_max=10.0,
            y_min=0.0, y_max=6.25,
            z_min=-10.0, z_max=5.0,
            max_rpm=10000,
            min_rpm=100,
            max_feed=110.0,
        ),
    ),
    TormachModel.PCNC_770: MachineProfile(
        model="PCNC 770",
        x_travel=12.0,
        y_travel=8.0,
        z_travel=10.25,
        min_rpm=175,
        max_rpm=10000,
        max_feed_ipm=110.0,
        envelope=MachineEnvelope(
            x_min=0.0, x_max=12.0,
            y_min=0.0, y_max=8.0,
            z_min=-10.25, z_max=5.0,
            max_rpm=10000,
            min_rpm=175,
            max_feed=110.0,
        ),
    ),
    TormachModel.PCNC_1100: MachineProfile(
        model="PCNC 1100",
        x_travel=18.0,
        y_travel=9.5,
        z_travel=16.25,
        min_rpm=175,
        max_rpm=10000,
        max_feed_ipm=135.0,
        envelope=MachineEnvelope(
            x_min=0.0, x_max=18.0,
            y_min=0.0, y_max=9.5,
            z_min=-16.25, z_max=5.0,
            max_rpm=10000,
            min_rpm=175,
            max_feed=135.0,
        ),
    ),
}


def get_profile(model: TormachModel) -> MachineProfile:
    return _PROFILES[model]


def list_profiles() -> list[MachineProfile]:
    return list(_PROFILES.values())
