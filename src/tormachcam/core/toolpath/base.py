"""Core toolpath data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class MoveType(Enum):
    """Type of CNC motion."""
    RAPID = "rapid"          # G0 — no cutting, full speed
    FEED = "feed"            # G1 — cutting feed
    PLUNGE = "plunge"        # G1 at Z feed — straight plunge into material
    RETRACT = "retract"      # G0 — pull out of material


@dataclass
class ToolpathPoint:
    """A single point the tool tip must pass through."""
    x: float
    y: float
    z: float
    move_type: MoveType = MoveType.FEED
    feed_rate: Optional[float] = None  # None → use segment default

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class ToolpathSegment:
    """A connected sequence of points, typically at one Z level."""
    points: list[ToolpathPoint] = field(default_factory=list)
    z_level: Optional[float] = None
    label: str = ""

    def append(self, pt: ToolpathPoint) -> None:
        self.points.append(pt)

    def is_empty(self) -> bool:
        return len(self.points) == 0


@dataclass
class Toolpath:
    """An ordered collection of toolpath segments making up one operation."""
    segments: list[ToolpathSegment] = field(default_factory=list)
    tool_number: int = 1
    operation_name: str = ""

    def add_segment(self, seg: ToolpathSegment) -> None:
        self.segments.append(seg)

    @property
    def total_points(self) -> int:
        return sum(len(s.points) for s in self.segments)

    @property
    def is_empty(self) -> bool:
        return all(s.is_empty() for s in self.segments)
