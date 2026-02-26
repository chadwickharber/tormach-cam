"""3D viewport widget using pyvistaqt for VTK-backed rendering.

VTK is initialized lazily after the window is shown to avoid blocking
the Qt event loop on startup.
"""

from __future__ import annotations

import numpy as np

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from ..core.toolpath.base import MoveType, Toolpath


class Viewport(QWidget):
    """Embeddable 3D viewport widget with lazy VTK initialization.

    On startup, displays a 'Loading…' placeholder while the window
    renders.  VTK is initialized on the first Qt event-loop tick after
    the window becomes visible, keeping the app startup instant.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stack: index 0 = placeholder, index 1 = VTK interactor
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack)

        self._placeholder = QLabel("Load an STL file to view the 3D model", self)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 14px;")
        self._stack.addWidget(self._placeholder)

        self._plotter = None
        self._mesh_actor = None
        self._toolpath_actors: list = []

        # Deferred geometry waiting for VTK to be ready
        self._pending_mesh: tuple | None = None
        self._pending_toolpaths: list | None = None

        # VTK is initialized on demand (when show_mesh is first called)
        # to keep startup instant.

    # ------------------------------------------------------------------
    # Lazy VTK setup
    # ------------------------------------------------------------------

    def _init_vtk(self) -> None:
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
        self._stack.setCurrentWidget(self._plotter.interactor)

        # Flush any geometry that arrived before VTK was ready
        if self._pending_mesh is not None:
            self.show_mesh(*self._pending_mesh)
            self._pending_mesh = None
        if self._pending_toolpaths is not None:
            self.show_toolpath(self._pending_toolpaths)
            self._pending_toolpaths = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_mesh(self, vertices: np.ndarray, faces: np.ndarray) -> None:
        """Display a trimesh-style mesh (Nx3 vertices, Mx3 face indices)."""
        if self._plotter is None:
            self._pending_mesh = (vertices, faces)
            self._placeholder.setText("Initializing 3D viewport…")
            QTimer.singleShot(0, self._init_vtk)
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
