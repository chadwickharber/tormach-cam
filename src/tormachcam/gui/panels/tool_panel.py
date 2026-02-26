"""Tool selection and parameters panel."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QWidget,
)

from ...config.defaults import build_default_tool_library
from ...core.tool import Tool, ToolLibrary


class ToolPanel(QWidget):
    """Panel for selecting and viewing cutting tool parameters."""

    tool_changed = pyqtSignal(object)  # Tool

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lib = build_default_tool_library()

        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Tool selector
        self._combo = QComboBox()
        for t in self._lib.list_tools():
            self._combo.addItem(f"T{t.number}: {t.name}", userData=t)
        self._combo.currentIndexChanged.connect(self._on_select)
        layout.addRow("Tool:", self._combo)

        # Display fields
        self._dia_lbl = QLabel()
        self._type_lbl = QLabel()
        self._rpm_spin = QSpinBox()
        self._rpm_spin.setRange(100, 10000)
        self._rpm_spin.setSingleStep(100)
        self._feed_xy_spin = QDoubleSpinBox()
        self._feed_xy_spin.setRange(0.1, 500.0)
        self._feed_xy_spin.setSingleStep(1.0)
        self._feed_z_spin = QDoubleSpinBox()
        self._feed_z_spin.setRange(0.1, 100.0)
        self._feed_z_spin.setSingleStep(0.5)

        layout.addRow("Diameter:", self._dia_lbl)
        layout.addRow("Type:", self._type_lbl)
        layout.addRow("RPM:", self._rpm_spin)
        layout.addRow("Feed XY:", self._feed_xy_spin)
        layout.addRow("Feed Z:", self._feed_z_spin)

        # Initialize with first tool
        if self._lib.list_tools():
            self._populate(self._lib.list_tools()[0])

    def tool_library(self) -> ToolLibrary:
        """Return the underlying ToolLibrary (for recommendation engine)."""
        return self._lib

    def current_tool(self) -> Tool | None:
        t = self._combo.currentData()
        if t is None:
            return None
        # Apply overrides
        t.default_rpm = self._rpm_spin.value()
        t.default_feed_xy = self._feed_xy_spin.value()
        t.default_feed_z = self._feed_z_spin.value()
        return t

    def _on_select(self, index: int) -> None:
        tool = self._combo.itemData(index)
        if tool is not None:
            self._populate(tool)
            self.tool_changed.emit(tool)

    def _populate(self, tool: Tool) -> None:
        self._dia_lbl.setText(f"{tool.diameter}")
        self._type_lbl.setText(tool.tool_type.value)
        self._rpm_spin.setValue(tool.default_rpm)
        self._feed_xy_spin.setValue(tool.default_feed_xy)
        self._feed_z_spin.setValue(tool.default_feed_z)
