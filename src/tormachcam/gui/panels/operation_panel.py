"""Operation parameters panel."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.operation import Operation, StrategyType
from ...core.tool import Tool


class OperationPanel(QWidget):
    """Panel for configuring machining operation parameters."""

    compute_requested = pyqtSignal(object)  # Operation

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setContentsMargins(8, 4, 8, 4)

        self._strategy_combo = QComboBox()
        self._strategy_combo.addItem("Roughing + Finishing", userData="both")
        self._strategy_combo.addItem("Roughing only", userData="roughing")
        self._strategy_combo.addItem("Finishing only", userData="finishing")
        form.addRow("Strategy:", self._strategy_combo)

        # Depth
        depth_group = QGroupBox("Depths")
        depth_form = QFormLayout(depth_group)
        self._z_top = QDoubleSpinBox()
        self._z_top.setRange(-100, 100)
        self._z_top.setValue(0.0)
        self._z_top.setSingleStep(0.01)
        self._z_bottom = QDoubleSpinBox()
        self._z_bottom.setRange(-100, 0)
        self._z_bottom.setValue(-0.25)
        self._z_bottom.setSingleStep(0.01)
        self._step_down = QDoubleSpinBox()
        self._step_down.setRange(0.001, 10.0)
        self._step_down.setValue(0.05)
        self._step_down.setSingleStep(0.01)
        depth_form.addRow("Z Top:", self._z_top)
        depth_form.addRow("Z Bottom:", self._z_bottom)
        depth_form.addRow("Step Down:", self._step_down)
        form.addRow(depth_group)

        # Radial
        self._step_over = QDoubleSpinBox()
        self._step_over.setRange(0.01, 1.0)
        self._step_over.setValue(0.4)
        self._step_over.setSingleStep(0.05)
        form.addRow("Step Over (fraction):", self._step_over)

        # Finish allowance
        self._finish_allowance = QDoubleSpinBox()
        self._finish_allowance.setRange(0.0, 0.5)
        self._finish_allowance.setValue(0.005)
        self._finish_allowance.setSingleStep(0.001)
        self._finish_allowance.setDecimals(4)
        form.addRow("Finish Allowance:", self._finish_allowance)

        # Clearance
        self._safe_z = QDoubleSpinBox()
        self._safe_z.setRange(0.01, 10.0)
        self._safe_z.setValue(0.1)
        self._safe_z.setSingleStep(0.05)
        self._rapid_z = QDoubleSpinBox()
        self._rapid_z.setRange(0.1, 10.0)
        self._rapid_z.setValue(0.5)
        self._rapid_z.setSingleStep(0.1)
        form.addRow("Safe Z:", self._safe_z)
        form.addRow("Rapid Z:", self._rapid_z)

        layout.addWidget(form_widget)

        # Compute button
        self._compute_btn = QPushButton("Compute Toolpaths")
        self._compute_btn.setEnabled(False)
        self._compute_btn.clicked.connect(self._on_compute)
        layout.addWidget(self._compute_btn)
        layout.addStretch()

        self._tool: Tool | None = None

    def set_tool(self, tool: Tool) -> None:
        self._tool = tool
        self._compute_btn.setEnabled(True)

    def _on_compute(self) -> None:
        if self._tool is None:
            return

        strategy_key = self._strategy_combo.currentData()
        strategies = {
            "roughing": [StrategyType.ROUGHING],
            "finishing": [StrategyType.FINISHING],
            "both": [StrategyType.ROUGHING, StrategyType.FINISHING],
        }[strategy_key]

        ops = []
        for s in strategies:
            ops.append(Operation(
                name=s.value.capitalize(),
                strategy=s,
                tool=self._tool,
                z_top=self._z_top.value(),
                z_bottom=self._z_bottom.value(),
                step_down=self._step_down.value(),
                step_over_fraction=self._step_over.value(),
                rpm=self._tool.default_rpm,
                feed_xy=self._tool.default_feed_xy,
                feed_z=self._tool.default_feed_z,
                safe_z=self._safe_z.value(),
                rapid_z=self._rapid_z.value(),
                finish_allowance=self._finish_allowance.value(),
            ))
        self.compute_requested.emit(ops)
