"""Tests for the PathPilot post-processor G-code output."""

import pytest
from shapely.geometry import Polygon

from tormachcam.core.toolpath.base import MoveType, Toolpath, ToolpathPoint, ToolpathSegment
from tormachcam.core.toolpath.roughing import RoughingParams, generate_roughing_toolpath
from tormachcam.core.units import Units
from tormachcam.gcode.pathpilot import PathPilotPostProcessor, PostProcessorConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_simple_toolpath() -> Toolpath:
    """A small artificial toolpath for testing the post-processor."""
    seg = ToolpathSegment(z_level=-0.05, label="test segment")
    seg.append(ToolpathPoint(0.5, 0.5, 0.1, MoveType.RAPID))
    seg.append(ToolpathPoint(0.5, 0.5, -0.05, MoveType.PLUNGE, 5.0))
    seg.append(ToolpathPoint(1.5, 0.5, -0.05, MoveType.FEED, 20.0))
    seg.append(ToolpathPoint(1.5, 1.5, -0.05, MoveType.FEED, 20.0))
    seg.append(ToolpathPoint(1.5, 1.5, 0.1, MoveType.RETRACT))

    tp = Toolpath(segments=[seg], tool_number=1, operation_name="test")
    return tp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPathPilotPostProcessor:
    def test_preamble_contains_required_codes(self):
        cfg = PostProcessorConfig(units=Units.INCH)
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])

        text = "\n".join(lines)
        assert "G17" in text
        assert "G20" in text       # inch mode
        assert "G40" in text
        assert "G49" in text
        assert "G54" in text
        assert "G80" in text
        assert "G90" in text
        assert "G94" in text
        assert "G64" in text       # path blending

    def test_mm_mode_uses_g21(self):
        cfg = PostProcessorConfig(units=Units.MM)
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        text = "\n".join(lines)
        assert "G21" in text

    def test_tool_change_sequence(self):
        cfg = PostProcessorConfig(tool_number=1, rpm=5000, coolant=True)
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])

        text = "\n".join(lines)
        assert "M5" in text        # spindle off before change
        assert "G30" in text       # Tormach tool change position (not G28)
        assert "T1 M6" in text     # tool change
        assert "G43 H1" in text    # tool length offset
        assert "S5000 M3" in text  # spindle start
        assert "M8" in text        # coolant on

    def test_no_g28_in_output(self):
        """Tormach uses G30, never G28."""
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        for line in lines:
            assert "G28" not in line

    def test_postamble_sequence(self):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])

        # Last few lines should be postamble
        tail = "\n".join(lines[-6:])
        assert "M5" in tail   # spindle off
        assert "M9" in tail   # coolant off
        assert "G30" in tail
        assert "M30" in tail  # end of program
        assert "%" in tail

    def test_rapid_moves_are_g0(self):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        # Find lines with RAPID/RETRACT points
        g0_lines = [l for l in lines if l.strip().startswith("G0")]
        assert len(g0_lines) > 0

    def test_feed_moves_are_g1(self):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        g1_lines = [l for l in lines if l.strip().startswith("G1")]
        assert len(g1_lines) > 0

    def test_feed_rate_included(self):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        f_lines = [l for l in lines if "F" in l and l.strip().startswith("G1")]
        assert len(f_lines) > 0

    def test_comments_use_parentheses(self):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([_make_simple_toolpath()])
        comment_lines = [l for l in lines if l.startswith("(")]
        assert len(comment_lines) > 0
        for cl in comment_lines:
            assert cl.endswith(")")

    def test_write_to_file(self, tmp_path):
        cfg = PostProcessorConfig()
        pp = PathPilotPostProcessor(cfg)
        out = tmp_path / "test.ngc"
        pp.generate([_make_simple_toolpath()], out)

        assert out.exists()
        content = out.read_text()
        assert content.endswith("\n")
        assert "G17" in content
        assert "M30" in content


class TestGCodeWithRealToolpath:
    """Integration test: roughing toolpath → post-processor."""

    def test_roughing_to_gcode_roundtrip(self):
        stock = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
        part = Polygon([(0.75, 0.75), (1.25, 0.75), (1.25, 1.25), (0.75, 1.25)])

        params = RoughingParams(
            tool_radius=0.25,
            step_over=0.2,
            step_down=0.05,
            feed_xy=20.0,
            feed_z=5.0,
            safe_z=0.1,
            rapid_z=0.5,
        )
        tp = generate_roughing_toolpath(
            stock_polygon=stock,
            part_contours=[part],
            z_levels=[-0.05],
            params=params,
        )

        cfg = PostProcessorConfig(
            units=Units.INCH,
            tool_number=1,
            rpm=3000,
        )
        pp = PathPilotPostProcessor(cfg)
        lines = pp.get_lines([tp])

        assert len(lines) > 10
        text = "\n".join(lines)
        assert "G0" in text
        assert "G1" in text
        assert "M30" in text
