"""Z-plane mesh slicer: trimesh → Shapely polygons.

The slicer is the critical 3D→2D bridge.  At each Z height it returns one
or more Shapely Polygon objects representing the cross-section of the mesh.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np
import trimesh
from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid


@dataclass
class SliceResult:
    """The 2D cross-section of a mesh at a given Z height."""

    z: float
    polygon: Polygon | MultiPolygon  # may be empty

    @property
    def is_empty(self) -> bool:
        return self.polygon.is_empty


def _path2d_to_shapely(path: trimesh.path.Path2D) -> Polygon | MultiPolygon:
    """Convert a trimesh Path2D (output of section()) to a Shapely geometry.

    trimesh.Path2D can contain multiple disconnected polygons; we use
    ``to_shapely()`` (trimesh>=4) or fall back to manual reconstruction.
    """
    try:
        geom = path.polygons_full
        if len(geom) == 0:
            return Polygon()
        polys = [make_valid(p) for p in geom]
        result = unary_union(polys)
        return result if result.is_valid else make_valid(result)
    except Exception as exc:
        warnings.warn(f"Shapely conversion failed: {exc}", stacklevel=3)
        return Polygon()


def slice_at_heights(
    mesh: trimesh.Trimesh,
    heights: Sequence[float],
) -> list[SliceResult]:
    """Slice *mesh* at each Z value in *heights*.

    Uses ``trimesh.section_multiplane`` for batched slicing (one BVH
    traversal instead of N individual section calls).

    Parameters
    ----------
    mesh:
        The trimesh.Trimesh to slice.
    heights:
        Iterable of Z values at which to cut.

    Returns
    -------
    List of SliceResult, one per height, in the same order as *heights*.
    Empty SliceResult objects are included for heights that miss the mesh.
    """
    heights = list(heights)
    if not heights:
        return []

    # section_multiplane takes a single origin/normal reference plane and a
    # list of scalar offsets along the normal.  With origin=[0,0,0] and
    # normal=[0,0,1], the offset values equal the absolute Z coordinates.
    sections = mesh.section_multiplane(
        plane_origin=[0.0, 0.0, 0.0],
        plane_normal=[0.0, 0.0, 1.0],
        heights=heights,
    )

    results: list[SliceResult] = []
    for z, path2d in zip(heights, sections):
        if path2d is None:
            results.append(SliceResult(z=z, polygon=Polygon()))
        else:
            poly = _path2d_to_shapely(path2d)
            results.append(SliceResult(z=z, polygon=poly))

    return results


def compute_z_levels(
    z_top: float,
    z_bottom: float,
    step_down: float,
) -> list[float]:
    """Generate Z levels from *z_top* downward by *step_down* increments.

    The first cut is at ``z_top - step_down``.  The final pass is always
    placed exactly at *z_bottom* (floor pass).

    Parameters
    ----------
    z_top:
        Top of stock (usually 0.0 for Tormach WCS).
    z_bottom:
        Deepest cut depth (negative in Tormach WCS, e.g. -0.5).
    step_down:
        Positive axial depth-of-cut per pass.

    Returns
    -------
    List of Z values in descending order (most shallow first).
    """
    if step_down <= 0:
        raise ValueError("step_down must be positive")
    if z_bottom >= z_top:
        raise ValueError("z_bottom must be less than z_top")

    levels: list[float] = []
    z = z_top - step_down
    while z > z_bottom + 1e-9:
        levels.append(round(z, 10))
        z -= step_down

    # Always include a final floor pass
    levels.append(round(z_bottom, 10))
    return levels
