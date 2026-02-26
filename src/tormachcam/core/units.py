"""Unit system enum and conversion helpers."""

from enum import Enum


class Units(Enum):
    INCH = "inch"
    MM = "mm"

    def to_mm(self, value: float) -> float:
        if self is Units.MM:
            return value
        return value * 25.4

    def from_mm(self, value: float) -> float:
        if self is Units.MM:
            return value
        return value / 25.4

    def label(self) -> str:
        return "in" if self is Units.INCH else "mm"

    @property
    def gcode_modal(self) -> str:
        """G-code modal group 6 word."""
        return "G20" if self is Units.INCH else "G21"
