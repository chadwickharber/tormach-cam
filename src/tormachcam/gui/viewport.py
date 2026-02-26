"""3D viewport widget using pyvistaqt for VTK-backed rendering."""

from __future__ import annotations

import numpy as np

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from ..core.toolpath.base import MoveType, Toolpath


class Viewport(QWidget):
    """Embeddable 3D viewport widget.

    VTK is initialized in the background warmup phase so that by the time
    the user clicks Load the render window is already live and the model
    appears instantly.

    Sequence
    --------
    1. App opens  → placeholder "Load a model…" shown
    2. PrevistaWarmupWorker.done  → warm_up() called
       - placeholder text changes to "Initialising 3D viewport…"
       - QTimer.singleShot schedules _init_vtk for next event loop tick
    3. _init_vtk runs on the main thread (OpenGL context setup)
       - placeholder restored to "Load a model…" once done
       - any pending geometry is flushed immediately
    4. User loads model → show_mesh() renders directly; no freeze
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        self._placeholder = QLabel("Load a model to view it in 3D", self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 14px;")
        self._stack.addWidget(self._placeholder)

        self._plotter = None
        self._pv = None
        self._mesh_actor = None
        self._toolpath_actors: list = []

        # Geometry that arrived before VTK was ready
        self._pending_mesh: tuple | None = None
        self._pending_toolpaths: list | None = None

    # ------------------------------------------------------------------
    # VTK initialisation (triggered by warmup worker, not by load)
    # ------------------------------------------------------------------

    def warm_up(self) -> None:
        """Called when PrevistaWarmupWorker.done fires.

        Updates the placeholder label and schedules _init_vtk on the
        next event-loop tick so the label repaint is visible first.
        """
        if self._plotter is not None:
            return  # already initialised
        self._placeholder.setText("Initialising 3D viewport…")
        QTimer.singleShot(0, self._init_vtk)

    def _init_vtk(self) -> None:
        if self._plotter is not None:
            return  # guard against double-init

        try:
            import pyvista as pv
            from pyvistaqt import QtInteractor
        except ImportError:
            self._placeholder.setText(
                "3D viewport unavailable\n(pip install pyvista pyvistaqt)"
            )
            return

        self._pv = pv
        self._plotter = QtInteractor(self)
        self._plotter.set_background("white")
        self._plotter.add_axes()

        self._stack.addWidget(self._plotter.interactor)
        # Stay on placeholder until we actually have geometry to show
        self._placeholder.setText("Load a model to view it in 3D")

        # Flush geometry that loaded while we were initialising
        if self._pending_mesh is not None:
            verts, faces = self._pending_mesh
            self._pending_mesh = None
            self.show_mesh(verts, faces)

        if self._pending_toolpaths is not None:
            tps = self._pending_toolpaths
            self._pending_toolpaths = None
            self.show_toolpath(tps)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_mesh(self, vertices: np.ndarray, faces: np.ndarray) -> None:
        """Display a trimesh-style mesh (Nx3 vertices, Mx3 face indices)."""
        if self._plotter is None:
            # VTK not ready yet — stash and wait for warm_up() to flush
            self._pending_mesh = (vertices, faces)
            return

        if self._mesh_actor is not None:
            self._plotter.remove_actor(self._mesh_actor)

        n_faces = len(faces)
        pv_faces = np.column_stack([
            np.full(n_faces, 3, dtype=np.int64), faces,
        ]).ravel()

        mesh = self._pv.PolyData(vertices, pv_faces)
        self._mesh_actor = self._plotter.add_mesh(
            mesh, color="lightblue", opacity=0.6, show_edges=False,
        )
        self._plotter.reset_camera()

        # Switch from placeholder to the live VTK view
        self._stack.setCurrentWidget(self._plotter.interactor)

    def show_toolpath(self, toolpaths: list[Toolpath]) -> None:
        """Overlay toolpath lines on the viewport."""
        if self._plotter is None:
            self._pending_toolpaths = toolpaths
            return

        for actor in self._toolpath_actors:
            self._plotter.remove_actor(actor)
        self._toolpath_actors.clear()

        for tp in toolpaths:
            for seg in tp.segments:
                if seg.is_empty():
                    continue

                feed_pts: list[list[float]] = []
                rapid_pts: list[list[float]] = []

                for pt in seg.points:
                    xyz = [pt.x, pt.y, pt.z]
                    if pt.move_type in (MoveType.RAPID, MoveType.RETRACT):
                        if len(feed_pts) >= 2:
                            self._add_polyline(feed_pts, "red")
                        feed_pts.clear()
                        rapid_pts.append(xyz)
                    else:
                        if len(rapid_pts) >= 2:
                            self._add_polyline(rapid_pts, "green")
                        rapid_pts.clear()
                        feed_pts.append(xyz)

                if len(feed_pts) >= 2:
                    self._add_polyline(feed_pts, "red")
                if len(rapid_pts) >= 2:
                    self._add_polyline(rapid_pts, "green")

        self._plotter.reset_camera()

    def clear(self) -> None:
        if self._plotter is not None:
            self._plotter.clear()
            self._plotter.add_axes()
            self._mesh_actor = None
            self._toolpath_actors.clear()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _add_polyline(self, points: list[list[float]], color: str) -> None:
        pts = np.array(points)
        n = len(pts)
        lines = np.zeros((n - 1, 3), dtype=np.int64)
        lines[:, 0] = 2
        lines[:, 1] = np.arange(n - 1)
        lines[:, 2] = np.arange(1, n)

        poly = self._pv.PolyData(pts, lines=lines.ravel())
        actor = self._plotter.add_mesh(
            poly, color=color, line_width=1.5, render_lines_as_tubes=False,
        )
        self._toolpath_actors.append(actor)
