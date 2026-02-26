"""Tests for G-code validation."""

import pytest

from tormachcam.core.toolpath.base import MoveType, Toolpath, ToolpathPoint, ToolpathSegment
from tormachcam.gcode.validate import MachineEnvelope, validate_toolpaths


@pytest.fixture
def small_envelope() -> MachineEnvelope:
    return MachineEnvelope(
        x_min=0.0, x_max=10.0,
        y_min=0.0, y_max=6.0,
        z_min=-10.0, z_max=0.0,
        max_rpm=10000,
        min_rpm=100,
        max_feed=110.0,
    )


def _make_tp(points: list[ToolpathPoint]) -> Toolpath:
    seg = ToolpathSegment(points=points, z_level=-0.05)
    return Toolpath(segments=[seg], operation_name="test")


class TestValidation:
    def test_valid_toolpath_passes(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 1.0, -0.05, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.is_ok

    def test_x_out_of_range(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(15.0, 1.0, -0.05, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.has_errors

    def test_y_out_of_range(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 8.0, -0.05, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.has_errors

    def test_z_out_of_range(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 1.0, -11.0, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.has_errors

    def test_rpm_too_low(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 1.0, -0.05, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=50)
        assert result.has_errors

    def test_rpm_too_high(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 1.0, -0.05, MoveType.FEED, 20.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=15000)
        assert result.has_errors

    def test_feed_too_high_is_warning(self, small_envelope):
        tp = _make_tp([
            ToolpathPoint(1.0, 1.0, -0.05, MoveType.FEED, 200.0),
        ])
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.has_warnings
        assert not result.has_errors

    def test_empty_toolpath_is_warning(self, small_envelope):
        tp = Toolpath(segments=[], operation_name="empty")
        result = validate_toolpaths([tp], small_envelope, rpm=3000)
        assert result.has_warnings
