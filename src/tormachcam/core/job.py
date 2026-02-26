"""Job orchestrator: ties model + stock + operations together.

The Job class is the top-level entry point for the CLI and GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .model import MeshModel, load_stl
from .operation import Operation, StrategyType
from .slicer import SliceResult, compute_z_levels, slice_at_heights
from .stock import Stock
from .toolpath.base import Toolpath
from .toolpath.finishing import FinishingParams, generate_finishing_toolpath
from .toolpath.roughing import RoughingParams, generate_roughing_toolpath
from .units import Units


@dataclass
class Job:
    """Represents a complete CAM job: model + stock + operations."""

    name: str = "Untitled"
    units: Units = Units.INCH
    model: Optional[MeshModel] = None
    stock: Optional[Stock] = None
    operations: list[Operation] = field(default_factory=list)

    def load_model(self, path: Path) -> MeshModel:
        self.model = load_stl(path)
        return self.model

    def compute_toolpaths(self) -> list[Toolpath]:
        """Run all operations and return the resulting toolpaths.

        Raises
        ------
        RuntimeError:
            If model or stock have not been set before calling.
        """
        if self.model is None:
            raise RuntimeError("No model loaded")
        if self.stock is None:
            raise RuntimeError("Stock not defined")

        toolpaths: list[Toolpath] = []

        for op in self.operations:
            z_levels = compute_z_levels(
                z_top=op.z_top,
                z_bottom=op.z_bottom,
                step_down=op.step_down,
            )

            # Slice the mesh at each Z level
            slice_results: list[SliceResult] = slice_at_heights(
                self.model.mesh, z_levels
            )
            part_contours = [sr.polygon for sr in slice_results]

            stock_poly = self.stock.as_shapely_polygon()

            if op.strategy is StrategyType.ROUGHING:
                params = RoughingParams(
                    tool_radius=op.tool.radius,
                    step_over=op.step_over,
                    step_down=op.step_down,
                    feed_xy=op.feed_xy,
                    feed_z=op.feed_z,
                    safe_z=op.safe_z,
                    rapid_z=op.rapid_z,
                    finish_allowance=op.finish_allowance,
                    raster_angle=op.raster_angle,
                )
                tp = generate_roughing_toolpath(
                    stock_polygon=stock_poly,
                    part_contours=part_contours,
                    z_levels=z_levels,
                    params=params,
                )
            else:
                params_f = FinishingParams(
                    tool_radius=op.tool.radius,
                    feed_xy=op.feed_xy,
                    feed_z=op.feed_z,
                    safe_z=op.safe_z,
                    rapid_z=op.rapid_z,
                )
                tp = generate_finishing_toolpath(
                    part_contours=part_contours,
                    z_levels=z_levels,
                    params=params_f,
                )

            tp.tool_number = op.tool.number
            tp.operation_name = op.name
            toolpaths.append(tp)

        return toolpaths
