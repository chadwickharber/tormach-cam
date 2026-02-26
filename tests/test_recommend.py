"""Tests for the auto tool/operation recommendation engine."""

from pathlib import Path

import numpy as np
import trimesh

from tormachcam.core.model import MeshModel
from tormachcam.core.operation import StrategyType
from tormachcam.core.recommend import recommend_operations
from tormachcam.core.tool import Tool, ToolLibrary, ToolType


def _make_model(extents):
    """Create a MeshModel from a box with given (x, y, z) extents."""
    mesh = trimesh.creation.box(extents=extents)
    return MeshModel(mesh=mesh, source_path=Path("test.stl"))


def _empty_library():
    lib = ToolLibrary.__new__(ToolLibrary)
    lib._path = None
    lib._tools = {}
    return lib


def _library_with(tools):
    lib = _empty_library()
    for t in tools:
        lib.add(t)
    return lib


class TestRecommendWithDefaults:
    """When library is empty, falls back to built-in defaults."""

    def test_returns_roughing_and_finishing(self):
        model = _make_model([2.0, 1.5, 0.75])
        rec = recommend_operations(model, _empty_library())
        assert len(rec.operations) == 2
        assert rec.operations[0].strategy == StrategyType.ROUGHING
        assert rec.operations[1].strategy == StrategyType.FINISHING

    def test_roughing_picks_largest_flat_endmill(self):
        model = _make_model([2.0, 1.5, 0.75])
        rec = recommend_operations(model, _empty_library())
        rough_op = rec.operations[0]
        # Default library has 1/2", 1/4", 1/8" flat + 1/4" ball.
        # Largest flat = 1/2" (T1)
        assert rough_op.tool.diameter == 0.5
        assert rough_op.tool.tool_type == ToolType.FLAT_ENDMILL

    def test_finishing_picks_ball_endmill(self):
        model = _make_model([2.0, 1.5, 0.75])
        rec = recommend_operations(model, _empty_library())
        finish_op = rec.operations[1]
        # Default library has 1/4" ball — it should be preferred for finishing
        assert finish_op.tool.tool_type == ToolType.BALL_ENDMILL

    def test_z_bottom_matches_depth(self):
        model = _make_model([3.0, 2.0, 1.0])
        rec = recommend_operations(model, _empty_library())
        for op in rec.operations:
            assert op.z_bottom == -1.0

    def test_roughing_has_finish_allowance(self):
        model = _make_model([2.0, 1.5, 0.5])
        rec = recommend_operations(model, _empty_library())
        rough_op = rec.operations[0]
        assert rough_op.finish_allowance == 0.005

    def test_summary_contains_extents(self):
        model = _make_model([2.0, 1.5, 0.75])
        rec = recommend_operations(model, _empty_library())
        assert any("2.000" in line for line in rec.summary)


class TestRecommendWithCustomLibrary:
    """Uses the provided library instead of defaults."""

    def test_single_tool_used_for_both(self):
        tool = Tool(
            number=10,
            name="3/8\" Flat",
            tool_type=ToolType.FLAT_ENDMILL,
            diameter=0.375,
            flute_count=3,
            default_rpm=4000,
            default_feed_xy=18.0,
            default_feed_z=4.0,
        )
        model = _make_model([1.0, 1.0, 0.5])
        rec = recommend_operations(model, _library_with([tool]))
        # Only flat endmill available — used for both rough + finish
        assert len(rec.operations) == 2
        assert rec.operations[0].tool.number == 10
        assert rec.operations[1].tool.number == 10

    def test_no_tools_returns_empty(self):
        """Library with only drills → no suitable tools."""
        drill = Tool(
            number=5,
            name="1/4\" Drill",
            tool_type=ToolType.DRILL,
            diameter=0.25,
            default_rpm=2000,
            default_feed_xy=0.0,
            default_feed_z=3.0,
        )
        model = _make_model([1.0, 1.0, 0.5])
        rec = recommend_operations(model, _library_with([drill]))
        assert len(rec.operations) == 0
        assert any("No suitable" in line for line in rec.summary)
