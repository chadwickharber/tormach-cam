"""Automatic tool and operation recommendations based on model geometry.

Analyses extents and depth of a loaded mesh and selects appropriate tools
from the user's ToolLibrary (or the built-in defaults if the library is empty).
Returns ready-to-run Operation objects plus a human-readable summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .model import MeshModel
from .operation import Operation, StrategyType
from .tool import Tool, ToolLibrary, ToolType


@dataclass
class Recommendation:
    """Result of the auto-recommendation pass."""

    operations: list[Operation]
    summary: list[str]  # Human-readable explanation lines


def _pick_roughing_tool(tools: list[Tool], depth: float) -> Optional[Tool]:
    """Largest flat endmill whose flute_length covers *depth* (if known)."""
    candidates = [
        t for t in tools
        if t.tool_type == ToolType.FLAT_ENDMILL
        and (t.flute_length == 0.0 or t.flute_length >= abs(depth))
    ]
    if not candidates:
        # Relax reach constraint — just pick largest flat endmill available
        candidates = [t for t in tools if t.tool_type == ToolType.FLAT_ENDMILL]
    if not candidates:
        return None
    return max(candidates, key=lambda t: t.diameter)


def _pick_finishing_tool(
    tools: list[Tool], roughing_tool: Optional[Tool]
) -> Optional[Tool]:
    """Ball or flat endmill, same diameter or smaller than roughing tool."""
    max_dia = roughing_tool.diameter if roughing_tool else 1.0
    candidates = [
        t for t in tools
        if t.tool_type in (ToolType.FLAT_ENDMILL, ToolType.BALL_ENDMILL)
        and t.diameter <= max_dia
    ]
    if not candidates:
        return None
    # Prefer ball endmill for finishing; fall back to smallest flat
    balls = [t for t in candidates if t.tool_type == ToolType.BALL_ENDMILL]
    if balls:
        return min(balls, key=lambda t: t.diameter)
    return min(candidates, key=lambda t: t.diameter)


def recommend_operations(
    model: MeshModel,
    library: ToolLibrary,
) -> Recommendation:
    """Analyse *model* and return recommended operations + explanation.

    Uses tools from *library*. Falls back to the built-in default tool
    set when the library contains no tools.
    """
    from ..config.defaults import build_default_tool_library

    tools = library.list_tools()
    if not tools:
        tools = build_default_tool_library().list_tools()

    ext = model.extents          # numpy (3,) — X, Y, Z sizes
    depth = float(ext[2])
    summary: list[str] = [
        f"Model extents: {float(ext[0]):.3f}\" x {float(ext[1]):.3f}\""
        f" x {float(ext[2]):.3f}\" deep",
    ]

    roughing_tool = _pick_roughing_tool(tools, depth)
    finishing_tool = _pick_finishing_tool(tools, roughing_tool)

    if roughing_tool is None and finishing_tool is None:
        summary.append("No suitable tools found in library.")
        return Recommendation(operations=[], summary=summary)

    ops: list[Operation] = []

    # ------------------------------------------------------------------
    # Roughing pass
    # ------------------------------------------------------------------
    if roughing_tool is not None:
        step_down = round(min(roughing_tool.diameter * 0.5, 0.05), 4)
        finish_allowance = 0.005 if finishing_tool is not None else 0.0

        ops.append(Operation(
            name=f"Roughing ({roughing_tool.name})",
            strategy=StrategyType.ROUGHING,
            tool=roughing_tool,
            z_top=0.0,
            z_bottom=-depth,
            step_down=step_down,
            step_over_fraction=0.4,
            rpm=roughing_tool.default_rpm,
            feed_xy=roughing_tool.default_feed_xy,
            feed_z=roughing_tool.default_feed_z,
            safe_z=0.1,
            rapid_z=0.5,
            finish_allowance=finish_allowance,
        ))
        summary.append(
            f"Roughing  → T{roughing_tool.number}: {roughing_tool.name}"
            f" | {roughing_tool.diameter}\" dia"
            f" | step-down {step_down:.3f}\""
            f" | step-over 40%"
            + (f" | +{finish_allowance}\" finish allowance" if finish_allowance else "")
        )

    # ------------------------------------------------------------------
    # Finishing pass
    # ------------------------------------------------------------------
    if finishing_tool is not None:
        step_down_f = round(finishing_tool.diameter * 0.25, 4)

        ops.append(Operation(
            name=f"Finishing ({finishing_tool.name})",
            strategy=StrategyType.FINISHING,
            tool=finishing_tool,
            z_top=0.0,
            z_bottom=-depth,
            step_down=step_down_f,
            rpm=finishing_tool.default_rpm,
            feed_xy=finishing_tool.default_feed_xy,
            feed_z=finishing_tool.default_feed_z,
            safe_z=0.1,
            rapid_z=0.5,
        ))
        summary.append(
            f"Finishing → T{finishing_tool.number}: {finishing_tool.name}"
            f" | {finishing_tool.diameter}\" dia"
        )

    return Recommendation(operations=ops, summary=summary)
