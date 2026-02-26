"""Tests for roughing and finishing toolpath generation."""

import pytest
from shapely.geometry import Polygon

from tormachcam.core.toolpath.base import MoveType, Toolpath
from tormachcam.core.toolpath.finishing import FinishingParams, generate_finishing_toolpath
from tormachcam.core.toolpath.roughing import RoughingParams, generate_roughing_toolpath


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def square_stock() -> Polygon:
    """2x2 inch square stock, lower-left at origin."""
    return Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])


@pytest.fixture
def small_part() -> Polygon:
    """0.5x0.5 inch part centred in the stock."""
    return Polygon([(0.75, 0.75), (1.25, 0.75), (1.25, 1.25), (0.75, 1.25)])


@pytest.fixture
def roughing_params() -> RoughingParams:
    return RoughingParams(
        tool_radius=0.25,
        step_over=0.2,
        step_down=0.05,
        feed_xy=20.0,
        feed_z=5.0,
        safe_z=0.1,
        rapid_z=0.5,
        finish_allowance=0.005,
    )


@pytest.fixture
def finishing_params() -> FinishingParams:
    return FinishingParams(
        tool_radius=0.25,
        feed_xy=15.0,
        feed_z=4.0,
        safe_z=0.1,
        rapid_z=0.5,
    )


# ---------------------------------------------------------------------------
# Roughing tests
# ---------------------------------------------------------------------------


class TestRoughing:
    def test_produces_toolpath(self, square_stock, small_part, roughing_params):
        z_levels = [-0.05, -0.10, -0.15]
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part] * len(z_levels),
            z_levels=z_levels,
            params=roughing_params,
        )
        assert isinstance(tp, Toolpath)
        assert not tp.is_empty

    def test_z_values_match_levels(self, square_stock, small_part, roughing_params):
        z_levels = [-0.05, -0.10]
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part, small_part],
            z_levels=z_levels,
            params=roughing_params,
        )
        all_z = {pt.z for seg in tp.segments for pt in seg.points
                 if pt.move_type == MoveType.FEED}
        # All feed moves should be at the expected Z levels or safe_z
        for z in all_z:
            assert z in z_levels or abs(z - roughing_params.safe_z) < 1e-6

    def test_starts_with_rapid(self, square_stock, small_part, roughing_params):
        """The very first move must be a rapid to safe_z."""
        z_levels = [-0.05]
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part],
            z_levels=z_levels,
            params=roughing_params,
        )
        first_point = tp.segments[0].points[0]
        assert first_point.move_type == MoveType.RAPID
        assert first_point.z == pytest.approx(roughing_params.safe_z)

    def test_ends_with_retract(self, square_stock, small_part, roughing_params):
        z_levels = [-0.05]
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part],
            z_levels=z_levels,
            params=roughing_params,
        )
        last_point = tp.segments[-1].points[-1]
        assert last_point.move_type == MoveType.RETRACT
        assert last_point.z == pytest.approx(roughing_params.safe_z)

    def test_plunge_feed_assigned(self, square_stock, small_part, roughing_params):
        z_levels = [-0.05]
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part],
            z_levels=z_levels,
            params=roughing_params,
        )
        plunges = [pt for seg in tp.segments for pt in seg.points
                   if pt.move_type == MoveType.PLUNGE]
        assert len(plunges) > 0
        for pt in plunges:
            assert pt.feed_rate == pytest.approx(roughing_params.feed_z)

    def test_empty_machinable_area(self, roughing_params):
        """When part fills the entire stock no toolpath should be generated."""
        stock = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        # Part is bigger than stock; nothing to machine
        part = stock.buffer(1.0)
        tp = generate_roughing_toolpath(
            stock_polygon=stock,
            part_contours=[part],
            z_levels=[-0.05],
            params=roughing_params,
        )
        assert tp.is_empty

    def test_single_z_level_reuses_contour(
        self, square_stock, small_part, roughing_params
    ):
        """Passing fewer contours than z_levels should not raise."""
        tp = generate_roughing_toolpath(
            stock_polygon=square_stock,
            part_contours=[small_part],   # only 1 contour for 3 levels
            z_levels=[-0.05, -0.10, -0.15],
            params=roughing_params,
        )
        assert not tp.is_empty


# ---------------------------------------------------------------------------
# Finishing tests
# ---------------------------------------------------------------------------


class TestFinishing:
    def test_produces_toolpath(self, small_part, finishing_params):
        z_levels = [-0.05, -0.10]
        tp = generate_finishing_toolpath(
            part_contours=[small_part, small_part],
            z_levels=z_levels,
            params=finishing_params,
        )
        assert not tp.is_empty

    def test_all_points_at_correct_z(self, small_part, finishing_params):
        z_levels = [-0.05]
        tp = generate_finishing_toolpath(
            part_contours=[small_part],
            z_levels=z_levels,
            params=finishing_params,
        )
        feed_z_values = {
            pt.z for seg in tp.segments for pt in seg.points
            if pt.move_type == MoveType.FEED
        }
        for z in feed_z_values:
            assert z == pytest.approx(-0.05)

    def test_closed_contour(self, small_part, finishing_params):
        """Finishing traces a closed loop: last FEED returns to plunge XY."""
        z_levels = [-0.05]
        tp = generate_finishing_toolpath(
            part_contours=[small_part],
            z_levels=z_levels,
            params=finishing_params,
        )
        # The plunge point is the loop entry; the last feed should close back to it
        for seg in tp.segments:
            plunge_pts = [pt for pt in seg.points if pt.move_type == MoveType.PLUNGE]
            feed_pts = [pt for pt in seg.points if pt.move_type == MoveType.FEED]
            if plunge_pts and len(feed_pts) > 1:
                entry = (plunge_pts[0].x, plunge_pts[0].y)
                last = (feed_pts[-1].x, feed_pts[-1].y)
                assert entry == pytest.approx(last, abs=1e-6)
                break

    def test_feed_rate_applied(self, small_part, finishing_params):
        z_levels = [-0.05]
        tp = generate_finishing_toolpath(
            part_contours=[small_part],
            z_levels=z_levels,
            params=finishing_params,
        )
        plunges = [pt for seg in tp.segments for pt in seg.points
                   if pt.move_type == MoveType.PLUNGE]
        assert all(pt.feed_rate == pytest.approx(finishing_params.feed_z)
                   for pt in plunges)

    def test_empty_polygon_produces_no_toolpath(self, finishing_params):
        empty = Polygon()
        tp = generate_finishing_toolpath(
            part_contours=[empty],
            z_levels=[-0.05],
            params=finishing_params,
        )
        assert tp.is_empty
