"""Tests for slicer.py.

Verifies that slicing known 3D shapes produces the expected 2D polygons.
"""

import numpy as np
import pytest
import trimesh
from shapely.geometry import MultiPolygon, Polygon

from tormachcam.core.slicer import compute_z_levels, slice_at_heights


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unit_cube() -> trimesh.Trimesh:
    """1x1x1 cube from (0,0,0) to (1,1,1)."""
    return trimesh.creation.box(extents=[1, 1, 1])


@pytest.fixture
def unit_cylinder() -> trimesh.Trimesh:
    """Cylinder: radius=0.5, height=1, centred at origin."""
    return trimesh.creation.cylinder(radius=0.5, height=1.0, sections=64)


# ---------------------------------------------------------------------------
# compute_z_levels
# ---------------------------------------------------------------------------


class TestComputeZLevels:
    def test_basic_levels(self):
        levels = compute_z_levels(z_top=0.0, z_bottom=-0.25, step_down=0.05)
        assert levels[0] == pytest.approx(-0.05)
        assert levels[-1] == pytest.approx(-0.25)
        assert len(levels) == 5

    def test_floor_always_included(self):
        levels = compute_z_levels(z_top=0.0, z_bottom=-0.1, step_down=0.03)
        assert levels[-1] == pytest.approx(-0.1)

    def test_invalid_step_down(self):
        with pytest.raises(ValueError, match="step_down"):
            compute_z_levels(0.0, -1.0, step_down=-0.1)

    def test_invalid_depths(self):
        with pytest.raises(ValueError, match="z_bottom"):
            compute_z_levels(0.0, 0.5, step_down=0.1)

    def test_descending_order(self):
        levels = compute_z_levels(0.0, -1.0, 0.2)
        assert all(levels[i] > levels[i + 1] for i in range(len(levels) - 1))


# ---------------------------------------------------------------------------
# slice_at_heights — cube
# ---------------------------------------------------------------------------


class TestSliceCube:
    def test_middle_slice_is_square(self, unit_cube):
        """Slice of a unit cube at z=0.5 should be roughly a 1x1 square."""
        # trimesh unit box is centred at origin: z = -0.5 to +0.5
        results = slice_at_heights(unit_cube, [0.0])
        assert len(results) == 1
        r = results[0]
        assert r.z == pytest.approx(0.0)
        assert not r.is_empty

        poly = r.polygon
        # Should be a Polygon or MultiPolygon
        assert isinstance(poly, (Polygon, MultiPolygon))

        # The cross-section area should be close to 1.0
        area = poly.area if isinstance(poly, Polygon) else sum(
            p.area for p in poly.geoms
        )
        assert area == pytest.approx(1.0, abs=0.02)

    def test_below_mesh_returns_empty(self, unit_cube):
        """Slicing below the mesh should return an empty polygon."""
        results = slice_at_heights(unit_cube, [-1.0])
        assert results[0].is_empty

    def test_above_mesh_returns_empty(self, unit_cube):
        results = slice_at_heights(unit_cube, [1.0])
        assert results[0].is_empty

    def test_multiple_heights(self, unit_cube):
        heights = [-0.4, -0.2, 0.0, 0.2, 0.4]
        results = slice_at_heights(unit_cube, heights)
        assert len(results) == 5
        for r in results:
            assert not r.is_empty

    def test_empty_heights(self, unit_cube):
        results = slice_at_heights(unit_cube, [])
        assert results == []


# ---------------------------------------------------------------------------
# slice_at_heights — cylinder
# ---------------------------------------------------------------------------


class TestSliceCylinder:
    def test_circle_cross_section(self, unit_cylinder):
        """Cylinder cross-section at z=0 should be roughly a circle of r=0.5."""
        results = slice_at_heights(unit_cylinder, [0.0])
        r = results[0]
        assert not r.is_empty

        poly = r.polygon
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda p: p.area)

        # Area of circle r=0.5 is π*0.25 ≈ 0.785
        assert poly.area == pytest.approx(np.pi * 0.25, abs=0.01)

    def test_centroid_near_origin(self, unit_cylinder):
        results = slice_at_heights(unit_cylinder, [0.0])
        poly = results[0].polygon
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda p: p.area)
        cx, cy = poly.centroid.x, poly.centroid.y
        assert cx == pytest.approx(0.0, abs=0.01)
        assert cy == pytest.approx(0.0, abs=0.01)
