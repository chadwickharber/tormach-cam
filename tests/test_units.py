"""Tests for units module."""

import pytest
from tormachcam.core.units import Units


class TestUnits:
    def test_inch_to_mm(self):
        assert Units.INCH.to_mm(1.0) == pytest.approx(25.4)

    def test_mm_to_mm(self):
        assert Units.MM.to_mm(25.4) == pytest.approx(25.4)

    def test_mm_from_mm(self):
        assert Units.MM.from_mm(10.0) == pytest.approx(10.0)

    def test_inch_from_mm(self):
        assert Units.INCH.from_mm(25.4) == pytest.approx(1.0)

    def test_gcode_modal_inch(self):
        assert Units.INCH.gcode_modal == "G20"

    def test_gcode_modal_mm(self):
        assert Units.MM.gcode_modal == "G21"

    def test_labels(self):
        assert Units.INCH.label() == "in"
        assert Units.MM.label() == "mm"
