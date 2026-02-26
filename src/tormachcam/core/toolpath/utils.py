"""Geometry helper utilities shared across toolpath strategies."""

from __future__ import annotations

import math

import numpy as np
from shapely.geometry import (
    LinearRing,
    LineString,
    MultiPolygon,
    Polygon,
    GeometryCollection,
)
from shapely.ops import unary_union
from shapely.validation import make_valid


def ensure_polygon(geom) -> Polygon | MultiPolygon:
    """Return a valid Polygon or MultiPolygon, or empty Polygon on failure."""
    if geom is None or geom.is_empty:
        return Polygon()
    if not geom.is_valid:
        geom = make_valid(geom)
    if isinstance(geom, (Polygon, MultiPolygon)):
        return geom
    if isinstance(geom, GeometryCollection):
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if polys:
            return unary_union(polys)
    return Polygon()


def polygon_to_exterior_coords(polygon: Polygon) -> list[tuple[float, float]]:
    """Return the exterior ring coords of *polygon* as a list of (x, y)."""
    return list(polygon.exterior.coords)


def ring_to_points_at_z(
    ring: LinearRing | list[tuple[float, float]],
    z: float,
) -> list[tuple[float, float, float]]:
    """Convert a 2D ring to 3D points at constant *z*."""
    coords = list(ring.coords) if isinstance(ring, LinearRing) else ring
    return [(x, y, z) for x, y in coords]


def iter_polygons(geom: Polygon | MultiPolygon):
    """Yield individual Polygon objects from a possibly Multi geometry."""
    if isinstance(geom, Polygon):
        if not geom.is_empty:
            yield geom
    elif isinstance(geom, MultiPolygon):
        for p in geom.geoms:
            if not p.is_empty:
                yield p


def chord_length(step_over: float, radius: float) -> float:
    """Chord length for a circular arc with given step-over and radius."""
    ratio = max(-1.0, min(1.0, 1.0 - step_over / radius))
    return 2.0 * radius * math.acos(ratio)


def raster_lines_in_bounds(
    xmin: float,
    xmax: float,
    ymin: float,
    ymax: float,
    step_over: float,
    angle_deg: float = 0.0,
) -> list[LineString]:
    """Generate parallel raster lines covering the given bounding box.

    Parameters
    ----------
    angle_deg:
        Rotation of raster direction in degrees (0 = horizontal X lines).

    Returns a list of LineString objects that fully span the bounding box
    when projected back to the original coordinate system.
    """
    # For non-zero angles we over-extend the lines and rely on clipping
    diagonal = math.hypot(xmax - xmin, ymax - ymin)
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2

    if angle_deg == 0.0:
        lines = []
        y = ymin
        while y <= ymax + 1e-9:
            lines.append(LineString([(xmin, y), (xmax, y)]))
            y += step_over
        return lines

    # Rotated raster
    angle_rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(angle_rad), math.sin(angle_rad)

    # Perpendicular direction
    perp_dx, perp_dy = -sin_a, cos_a

    n = int(math.ceil(diagonal / step_over)) + 1
    lines = []
    for i in range(-n, n + 1):
        offset = i * step_over
        # Center of this raster line
        lx = cx + offset * perp_dx
        ly = cy + offset * perp_dy
        # Extend along raster direction beyond the diagonal
        p1 = (lx - cos_a * diagonal, ly - sin_a * diagonal)
        p2 = (lx + cos_a * diagonal, ly + sin_a * diagonal)
        lines.append(LineString([p1, p2]))

    return lines
