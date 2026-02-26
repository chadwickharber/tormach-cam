"""3D viewport widget using pyvistaqt for VTK-backed rendering.

Displays the loaded STL mesh and generated toolpath lines inside a
dock-able Qt widget.
"""

from __future__ import annotations

import numpy as np

from PyQt6.QtWidgets import QWidget, QVBoxLayout

try:
    import pyvista as pv
    from pyvistaqt import QtInteractor

    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False

from ..core.toolpath.base import MoveType, Toolpath


class Viewport(QWidget):
    """Embeddable 3D viewport widget.

    Falls back to a simple placeholder label if pyvista/pyvistaqt are not
    installed, so the rest of the GUI still works.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plotter: QtInteractor | None = None
        self._mesh_actor = None
        self._toolpath_actors: list = []

        if HAS_PYVISTA:
            self._plotter = QtInteractor(self)
            layout.addWidget(self._plotter.interactor)
            self._plotter.set_background("white")
            self._plotter.add_axes()
        else:
            from PyQt6.QtWidgets import QLabel
            from PyQt6.QtCore import Qt

            lbl = QLabel("3D viewport requires pyvista + pyvistaqt", self)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)

    def show_mesh(self, vertices: np.ndarray, faces: np.ndarray) -> None:
        """Display a trimesh-style mesh (Nx3 vertices, Mx3 face indices)."""
        if self._plotter is None:
            return

        # Clear previous mesh
        if self._mesh_actor is not None:
            self._plotter.remove_actor(self._mesh_actor)

        # pyvista wants faces in [n, v0, v1, v2, ...] format
        n_faces = len(faces)
        pv_faces = np.column_stack([
            np.full(n_faces, 3, dtype=np.int64), faces,
        ]).ravel()

        mesh = pv.PolyData(vertices, pv_faces)
        self._mesh_actor = self._plotter.add_mesh(
            mesh,
            color="lightblue",
            opacity=0.6,
            show_edges=False,
        )
        self._plotter.reset_camera()

    def show_toolpath(self, toolpaths: list[Toolpath]) -> None:
        """Overlay toolpath lines on the viewport."""
        if self._plotter is None:
            return

        # Remove old toolpath actors
        for actor in self._toolpath_actors:
            self._plotter.remove_actor(actor)
        self._toolpath_actors.clear()

        feed_color = "red"
        rapid_color = "green"

        for tp in toolpaths:
            for seg in tp.segments:
                if seg.is_empty():
                    continue

                feed_pts: list[list[float]] = []
                rapid_pts: list[list[float]] = []

                for pt in seg.points:
                    xyz = [pt.x, pt.y, pt.z]
                    if pt.move_type in (MoveType.RAPID, MoveType.RETRACT):
                        # Flush feed buffer
                        if len(feed_pts) >= 2:
                            self._add_polyline(feed_pts, feed_color)
                        feed_pts.clear()
                        rapid_pts.append(xyz)
                    else:
                        # Flush rapid buffer
                        if len(rapid_pts) >= 2:
                            self._add_polyline(rapid_pts, rapid_color)
                        rapid_pts.clear()
                        feed_pts.append(xyz)

                # Flush remaining buffers
                if len(feed_pts) >= 2:
                    self._add_polyline(feed_pts, feed_color)
                if len(rapid_pts) >= 2:
                    self._add_polyline(rapid_pts, rapid_color)

        self._plotter.reset_camera()

    def _add_polyline(self, points: list[list[float]], color: str) -> None:
        pts = np.array(points)
        n = len(pts)
        lines = np.zeros((n - 1, 3), dtype=np.int64)
        lines[:, 0] = 2
        lines[:, 1] = np.arange(n - 1)
        lines[:, 2] = np.arange(1, n)

        poly = pv.PolyData(pts, lines=lines.ravel())
        actor = self._plotter.add_mesh(
            poly, color=color, line_width=1.5, render_lines_as_tubes=False,
        )
        self._toolpath_actors.append(actor)

    def clear(self) -> None:
        if self._plotter is not None:
            self._plotter.clear()
            self._plotter.add_axes()
            self._mesh_actor = None
            self._toolpath_actors.clear()
