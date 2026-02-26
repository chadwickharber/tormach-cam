"""Main application window with docked panel layout."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QStatusBar,
)

from ..core.job import Job
from ..core.model import MeshModel
from ..core.stock import Stock
from ..gcode.pathpilot import PathPilotPostProcessor, PostProcessorConfig

from .panels.gcode_panel import GCodePanel
from .panels.model_panel import ModelPanel
from .panels.operation_panel import OperationPanel
from .panels.tool_panel import ToolPanel
from .viewport import Viewport
from .workers import LoadModelWorker, PrevistaWarmupWorker, ToolpathWorker


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

        # Pre-import pyvista/VTK modules in a background thread, then
        # immediately initialise the QtInteractor (OpenGL context) on the
        # main thread once imports are done.  This means the ~3s VTK freeze
        # happens right after launch — not when the user clicks Load.
        self._warmup = PrevistaWarmupWorker(parent=self)
        self._warmup.done.connect(self._viewport.warm_up)
        self._warmup.start()

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
        # Model panel now emits a Path, not a loaded model
        self._model_panel.load_requested.connect(self._start_load_worker)

        self._tool_panel.tool_changed.connect(self._op_panel.set_tool)
        self._op_panel.compute_requested.connect(self._on_compute_requested)

        # Set initial tool in operation panel
        tool = self._tool_panel.current_tool()
        if tool is not None:
            self._op_panel.set_tool(tool)

    # ------------------------------------------------------------------
    # Async model loading
    # ------------------------------------------------------------------

    def _start_load_worker(self, path: Path) -> None:
        """Kick off a background thread to load + decimate the mesh."""
        self._model_panel.set_loading(True)
        self._gcode_panel.clear()
        self._status.showMessage(f"Loading {path.name}…")

        self._load_worker = LoadModelWorker(path, parent=self)
        self._load_worker.finished.connect(self._on_model_loaded)
        self._load_worker.error.connect(self._on_load_error)
        self._load_worker.progress.connect(self._status.showMessage)
        self._load_worker.start()

    def _on_model_loaded(self, model: MeshModel) -> None:
        self._model = model
        self._job.model = model

        self._model_panel.set_loading(False)
        self._model_panel.update_model(model)

        # Auto-create stock that wraps the model
        self._job.stock = Stock.from_model_bounds(
            model.bounds, margin=0.1, z_top=0.0
        )

        # Display the *decimated* mesh in the viewport
        self._viewport.show_mesh(model.display_vertices, model.display_faces)

        self._status.showMessage(
            f"Loaded {model.source_path.name}  "
            f"({len(model.mesh.vertices):,} verts, "
            f"{len(model.mesh.faces):,} faces)"
        )

        # Auto-recommend tools and generate G-code
        self._run_auto_recommend()

    def _on_load_error(self, message: str) -> None:
        self._model_panel.set_loading(False)
        self._status.showMessage(f"Error: {message}")
        QMessageBox.critical(self, "Load Error", message)

    # ------------------------------------------------------------------
    # Auto tool recommendation
    # ------------------------------------------------------------------

    def _run_auto_recommend(self) -> None:
        """Analyse the loaded model, pick tools, and auto-generate G-code."""
        from ..core.recommend import recommend_operations

        library = self._tool_panel.tool_library()
        rec = recommend_operations(self._model, library)

        if not rec.operations:
            self._status.showMessage(
                "Could not auto-recommend tools. "
                "Select a tool manually and click Compute."
            )
            return

        # Show the recommendation summary in the G-code panel while we compute
        preview = (
            ["( === TormachCAM Auto-Recommendation === )"]
            + [f"( {line} )" for line in rec.summary]
            + ["", "( Computing toolpaths… )"]
        )
        self._gcode_panel.set_gcode(preview)

        self._status.showMessage(
            "Auto-recommending: " + " | ".join(rec.summary[:2])
        )

        # Kick off toolpath computation with recommended operations
        self._on_compute_requested(rec.operations)

    # ------------------------------------------------------------------
    # Manual / auto toolpath computation
    # ------------------------------------------------------------------

    def _on_compute_requested(self, operations: list) -> None:
        if self._job.model is None:
            QMessageBox.warning(self, "No Model", "Load a model first.")
            return

        self._job.operations = operations
        self._status.showMessage("Computing toolpaths…")

        self._worker = ToolpathWorker(self._job, parent=self)
        self._worker.finished.connect(self._on_toolpaths_ready)
        self._worker.error.connect(self._on_worker_error)
        self._worker.progress.connect(self._status.showMessage)
        self._worker.start()

    def _on_toolpaths_ready(self, toolpaths: list) -> None:
        self._viewport.show_toolpath(toolpaths)

        # Generate G-code for each toolpath using its own tool number
        all_lines: list[str] = []
        for tp in toolpaths:
            tool = self._tool_panel.current_tool()
            cfg = PostProcessorConfig(
                units=self._job.units,
                tool_number=tp.tool_number,
                rpm=tool.default_rpm if tool else 3000,
            )
            post = PathPilotPostProcessor(cfg)
            all_lines.extend(post.get_lines([tp]))

        self._gcode_panel.set_gcode(all_lines)

        total_pts = sum(t.total_points for t in toolpaths)
        self._status.showMessage(
            f"Done: {len(toolpaths)} operation(s), "
            f"{total_pts:,} points, {len(all_lines):,} G-code lines"
        )

    def _on_worker_error(self, message: str) -> None:
        self._status.showMessage(f"Error: {message}")
        QMessageBox.critical(self, "Computation Error", message)
