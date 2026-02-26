"""Main application window with docked panel layout."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QWidget,
)

from ..core.job import Job
from ..core.model import MeshModel
from ..core.operation import StrategyType
from ..core.stock import Stock
from ..core.units import Units
from ..gcode.pathpilot import PathPilotPostProcessor, PostProcessorConfig

from .panels.gcode_panel import GCodePanel
from .panels.model_panel import ModelPanel
from .panels.operation_panel import OperationPanel
from .panels.tool_panel import ToolPanel
from .viewport import Viewport
from .workers import LoadModelWorker, ToolpathWorker


class MainWindow(QMainWindow):
    """Top-level application window.

    Layout
    ------
    Left dock:   Model → Tool → Operation panels (stacked)
    Center:      3D Viewport
    Bottom dock: G-code preview
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("TormachCAM")
        self.resize(1280, 800)

        self._job: Job = Job()
        self._model: MeshModel | None = None
        self._worker: ToolpathWorker | None = None
        self._load_worker: LoadModelWorker | None = None

        self._setup_ui()
        self._connect_signals()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        # Central viewport
        self._viewport = Viewport(self)
        self.setCentralWidget(self._viewport)

        # Left dock — control panels
        self._model_panel = ModelPanel()
        self._tool_panel = ToolPanel()
        self._op_panel = OperationPanel()

        for panel, title in [
            (self._model_panel, "Model"),
            (self._tool_panel, "Tool"),
            (self._op_panel, "Operation"),
        ]:
            dock = QDockWidget(title, self)
            dock.setWidget(panel)
            dock.setFeatures(
                QDockWidget.DockWidgetFeature.DockWidgetMovable |
                QDockWidget.DockWidgetFeature.DockWidgetFloatable,
            )
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

        # Bottom dock — G-code panel
        self._gcode_panel = GCodePanel()
        gcode_dock = QDockWidget("G-Code", self)
        gcode_dock.setWidget(self._gcode_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, gcode_dock)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("Ready")

    def _connect_signals(self) -> None:
        self._model_panel.model_loaded.connect(self._on_model_loaded)
        self._tool_panel.tool_changed.connect(self._op_panel.set_tool)
        self._op_panel.compute_requested.connect(self._on_compute_requested)

        # Set initial tool in operation panel
        tool = self._tool_panel.current_tool()
        if tool is not None:
            self._op_panel.set_tool(tool)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_model_loaded(self, model: MeshModel) -> None:
        self._model = model
        self._job.model = model

        # Auto-create stock
        self._job.stock = Stock.from_model_bounds(
            model.bounds, margin=0.1, z_top=0.0
        )

        # Display in viewport
        self._viewport.show_mesh(
            model.mesh.vertices.astype(float),
            model.mesh.faces,
        )

        self._status.showMessage(
            f"Loaded {model.source_path.name}  "
            f"({len(model.mesh.vertices)} verts)"
        )

    def _on_compute_requested(self, operations: list) -> None:
        if self._job.model is None:
            QMessageBox.warning(self, "No Model", "Load an STL file first.")
            return

        self._job.operations = operations
        self._status.showMessage("Computing toolpaths...")
        self._gcode_panel.clear()

        self._worker = ToolpathWorker(self._job, parent=self)
        self._worker.finished.connect(self._on_toolpaths_ready)
        self._worker.error.connect(self._on_worker_error)
        self._worker.progress.connect(self._status.showMessage)
        self._worker.start()

    def _on_toolpaths_ready(self, toolpaths: list) -> None:
        self._viewport.show_toolpath(toolpaths)

        # Generate G-code
        tool = self._tool_panel.current_tool()
        cfg = PostProcessorConfig(
            units=self._job.units,
            tool_number=tool.number if tool else 1,
            rpm=tool.default_rpm if tool else 3000,
        )
        post = PathPilotPostProcessor(cfg)
        lines = post.get_lines(toolpaths)
        self._gcode_panel.set_gcode(lines)

        self._status.showMessage(
            f"Done: {sum(t.total_points for t in toolpaths)} points, "
            f"{len(lines)} G-code lines"
        )

    def _on_worker_error(self, message: str) -> None:
        self._status.showMessage(f"Error: {message}")
        QMessageBox.critical(self, "Computation Error", message)
