"""Contour-parallel finishing strategy.

At each Z level the part contour is offset outward by the tool radius to
produce the cutter-centerline path.  Exterior and interior rings are traced
as closed contour passes.
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import MultiPolygon, Polygon

from .base import MoveType, Toolpath, ToolpathPoint, ToolpathSegment
from .utils import ensure_polygon, iter_polygons


@dataclass
class FinishingParams:
    """Parameters for the contour-parallel finishing strategy."""

    tool_radius: float
    feed_xy: float
    feed_z: float
    safe_z: float
    rapid_z: float
    extra_offset: float = 0.0  # spring-pass offset (usually 0)


def generate_finishing_toolpath(
    part_contours: list[Polygon | MultiPolygon],
    z_levels: list[float],
    params: FinishingParams,
) -> Toolpath:
    """Generate contour-parallel finishing passes.

    Parameters
    ----------
    part_contours:
        Part cross-section at each Z level.
    z_levels:
        Descending list of Z depths.
    params:
        Finishing parameters.

    Returns
    -------
    A Toolpath with contour segments.
    """
    toolpath = Toolpath(operation_name="finishing")
    offset = params.tool_radius + params.extra_offset

    for i, z in enumerate(z_levels):
        contour_idx = min(i, len(part_contours) - 1)
        part_poly = part_contours[contour_idx]

        for poly in iter_polygons(part_poly):
            # Offset outward to get cutter centerline
            centerline = poly.buffer(offset)
            centerline = ensure_polygon(centerline)
            if centerline.is_empty:
                continue

            for cpoly in iter_polygons(centerline):
                # Trace exterior ring
                seg = _trace_ring(
                    list(cpoly.exterior.coords), z, params,
                    label=f"finish ext z={z:.4f}",
                )
                if not seg.is_empty():
                    toolpath.add_segment(seg)

                # Trace each interior ring (pockets/holes)
                for interior in cpoly.interiors:
                    seg = _trace_ring(
                        list(interior.coords), z, params,
                        label=f"finish int z={z:.4f}",
                    )
                    if not seg.is_empty():
                        toolpath.add_segment(seg)

    return toolpath


def _trace_ring(
    coords: list[tuple[float, float]],
    z: float,
    params: FinishingParams,
    label: str = "",
) -> ToolpathSegment:
    """Trace a closed 2D ring at *z* with proper approach and retract."""
    if len(coords) < 2:
        return ToolpathSegment(z_level=z, label=label)

    seg = ToolpathSegment(z_level=z, label=label)

    x0, y0 = coords[0]

    # Rapid to position, plunge
    seg.append(ToolpathPoint(x0, y0, params.safe_z, MoveType.RAPID))
    seg.append(ToolpathPoint(x0, y0, z, MoveType.PLUNGE, params.feed_z))

    # Feed around the contour
    for x, y in coords[1:]:
        seg.append(ToolpathPoint(x, y, z, MoveType.FEED, params.feed_xy))

    # Close the loop back to start
    if (coords[-1][0], coords[-1][1]) != (x0, y0):
        seg.append(ToolpathPoint(x0, y0, z, MoveType.FEED, params.feed_xy))

    # Retract
    seg.append(ToolpathPoint(x0, y0, params.safe_z, MoveType.RETRACT))

    return seg
