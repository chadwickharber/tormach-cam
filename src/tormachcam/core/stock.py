"""Stock (workpiece blank) definition."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Stock:
    """Rectangular stock definition.

    All dimensions are in the job's native units (inch or mm).
    Z=0 is the **top** of the stock, which is the Tormach convention.
    Negative Z values go down into the material.

    Parameters
    ----------
    x_size, y_size, z_size:
        Bounding dimensions of the stock block.
    x_origin, y_origin:
        XY offset of the stock's lower-left corner from the WCS origin.
    z_top:
        Z coordinate of the top face of stock in WCS.  Defaults to 0.0.
    """

    x_size: float
    y_size: float
    z_size: float
    x_origin: float = 0.0
    y_origin: float = 0.0
    z_top: float = 0.0

    @property
    def z_bottom(self) -> float:
        return self.z_top - self.z_size

    @property
    def x_min(self) -> float:
        return self.x_origin

    @property
    def x_max(self) -> float:
        return self.x_origin + self.x_size

    @property
    def y_min(self) -> float:
        return self.y_origin

    @property
    def y_max(self) -> float:
        return self.y_origin + self.y_size

    @property
    def bounds_2d(self) -> tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax) of the stock footprint."""
        return (self.x_min, self.y_min, self.x_max, self.y_max)

    def as_shapely_polygon(self):
        """Return a Shapely Polygon of the stock XY footprint."""
        from shapely.geometry import box

        return box(self.x_min, self.y_min, self.x_max, self.y_max)

    @classmethod
    def from_model_bounds(
        cls,
        bounds: np.ndarray,
        margin: float = 0.0,
        z_top: float = 0.0,
    ) -> "Stock":
        """Create stock that fits around *bounds* with optional *margin*."""
        xmin, ymin, zmin = bounds[0]
        xmax, ymax, zmax = bounds[1]
        return cls(
            x_size=xmax - xmin + 2 * margin,
            y_size=ymax - ymin + 2 * margin,
            z_size=zmax - zmin,
            x_origin=xmin - margin,
            y_origin=ymin - margin,
            z_top=z_top,
        )
