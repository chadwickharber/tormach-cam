"""Machining operation parameter containers.

An Operation binds a strategy (roughing/finishing) to a tool and a set of
parameters.  The Job orchestrator iterates over operations to produce
toolpaths.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .tool import Tool


class StrategyType(Enum):
    ROUGHING = "roughing"
    FINISHING = "finishing"


@dataclass
class Operation:
    """Parameters for a single machining operation."""

    name: str
    strategy: StrategyType
    tool: Tool

    # Depth parameters
    z_top: float = 0.0        # start Z (usually stock top = 0)
    z_bottom: float = -0.25   # final depth

    # Axial step
    step_down: float = 0.05

    # Radial step (only for roughing; fraction of tool diameter)
    step_over_fraction: float = 0.4

    # Feeds & speeds
    rpm: int = 3000
    feed_xy: float = 20.0
    feed_z: float = 5.0

    # Clearance planes
    safe_z: float = 0.1       # between cuts at the same level
    rapid_z: float = 0.5      # between operations / levels

    # Finishing
    finish_allowance: float = 0.0   # extra stock left by roughing
    raster_angle: float = 0.0       # roughing raster direction (degrees)

    @property
    def step_over(self) -> float:
        """Absolute step-over distance (XY)."""
        return self.tool.diameter * self.step_over_fraction
