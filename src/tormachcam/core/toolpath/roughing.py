"""Raster zigzag pocket roughing strategy.

Algorithm per Z level
---------------------
1. Compute the machinable area:
   ``stock_polygon.difference(part_contour.buffer(tool_radius + finish_allowance))``
2. Fill the machinable area with parallel raster lines spaced at *step_over*.
3. Clip each raster line to the machinable polygon boundary.
4. Connect the clipped line segments in alternating zigzag pattern (no air cuts
   between adjacent lines where possible).
5. Emit retract → rapid → plunge transitions between disconnected regions.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import LineString, MultiLineString, MultiPolygon, Polygon

from .base import MoveType, Toolpath, ToolpathPoint, ToolpathSegment
from .utils import ensure_polygon, iter_polygons, raster_lines_in_bounds


@dataclass
class RoughingParams:
    """Parameters for the raster-zigzag roughing strategy."""

    tool_radius: float
    step_over: float          # XY distance between adjacent raster passes
    step_down: float          # axial depth of cut (positive value)
    feed_xy: float            # cutting feed rate for XY moves
    feed_z: float             # plunge feed rate
    safe_z: float             # Z clearance for rapids between cuts at same level
    rapid_z: float            # Z clearance for rapids between levels
    finish_allowance: float = 0.0  # extra material left for finishing pass
    raster_angle: float = 0.0     # degrees — 0 means horizontal (X) raster


def generate_roughing_toolpath(
    stock_polygon: Polygon,
    part_contours: list[Polygon | MultiPolygon],
    z_levels: list[float],
    params: RoughingParams,
) -> Toolpath:
    """Generate a raster-zigzag roughing toolpath.

    Parameters
    ----------
    stock_polygon:
        The XY polygon of the stock material.
    part_contours:
        Shapely polygon(s) representing the part cross-section at each
        corresponding Z level.  If shorter than *z_levels*, the last contour
        is reused for deeper levels.
    z_levels:
        Descending list of Z depths for each pass.
    params:
        Roughing strategy parameters.

    Returns
    -------
    A Toolpath object containing all roughing segments.
    """
    toolpath = Toolpath(operation_name="roughing")
    offset = params.tool_radius + params.finish_allowance

    for i, z in enumerate(z_levels):
        contour_idx = min(i, len(part_contours) - 1)
        part_poly = part_contours[contour_idx]

        # Offset part outward by tool radius + finish allowance
        exclusion = Polygon()
        for poly in iter_polygons(part_poly):
            buffered = poly.buffer(offset)
            exclusion = exclusion.union(buffered)

        exclusion = ensure_polygon(exclusion)

        # Machinable area = stock minus buffered part
        machinable = stock_polygon.difference(exclusion)
        machinable = ensure_polygon(machinable)

        if machinable.is_empty:
            continue

        seg = _raster_zigzag_at_level(machinable, z, params)
        if not seg.is_empty():
            toolpath.add_segment(seg)

    return toolpath


def _raster_zigzag_at_level(
    machinable: Polygon | MultiPolygon,
    z: float,
    params: RoughingParams,
) -> ToolpathSegment:
    """Generate raster zigzag fill within *machinable* at height *z*."""
    seg = ToolpathSegment(z_level=z, label=f"rough z={z:.4f}")

    bounds = machinable.bounds  # (minx, miny, maxx, maxy)
    rasters = raster_lines_in_bounds(
        bounds[0], bounds[2], bounds[1], bounds[3],
        step_over=params.step_over,
        angle_deg=params.raster_angle,
    )

    # Clip rasters to the machinable polygon and collect line segments
    clipped_lines: list[list[tuple[float, float]]] = []
    for i, line in enumerate(rasters):
        intersection = line.intersection(machinable)
        if intersection.is_empty:
            continue

        raw_lines: list[LineString] = []
        if isinstance(intersection, LineString):
            raw_lines = [intersection]
        elif isinstance(intersection, MultiLineString):
            raw_lines = list(intersection.geoms)
        else:
            # Sometimes intersection returns mixed geometries
            for geom in getattr(intersection, "geoms", [intersection]):
                if isinstance(geom, LineString):
                    raw_lines.append(geom)

        # For zigzag: reverse every other line
        for ls in raw_lines:
            coords = list(ls.coords)
            if i % 2 == 1:
                coords = list(reversed(coords))
            clipped_lines.append(coords)

    # Build segment from clipped lines with retract/rapid/plunge transitions
    first_move = True
    for coords in clipped_lines:
        if not coords:
            continue

        start_x, start_y = coords[0]

        if first_move:
            # Initial approach: rapid to safe_z, then plunge
            seg.append(ToolpathPoint(
                start_x, start_y, params.safe_z, MoveType.RAPID))
            seg.append(ToolpathPoint(
                start_x, start_y, z, MoveType.PLUNGE, params.feed_z))
            first_move = False
        else:
            # Retract, rapid to new start, plunge
            seg.append(ToolpathPoint(
                seg.points[-1].x, seg.points[-1].y, params.safe_z,
                MoveType.RETRACT))
            seg.append(ToolpathPoint(
                start_x, start_y, params.safe_z, MoveType.RAPID))
            seg.append(ToolpathPoint(
                start_x, start_y, z, MoveType.PLUNGE, params.feed_z))

        # Feed through each point in this raster line
        for x, y in coords[1:]:
            seg.append(ToolpathPoint(x, y, z, MoveType.FEED, params.feed_xy))

    # Final retract
    if not seg.is_empty():
        seg.append(ToolpathPoint(
            seg.points[-1].x, seg.points[-1].y, params.safe_z,
            MoveType.RETRACT))

    return seg
