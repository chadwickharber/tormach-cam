"""Model info panel: shows mesh stats and a Load button."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QPushButton,
    QWidget,
)


class ModelPanel(QWidget):
    """Displays model information and provides a load button.

    Emits ``load_requested`` with the chosen Path; the actual loading
    happens off the main thread in MainWindow via LoadModelWorker.
    """

    load_requested = pyqtSignal(object)  # pathlib.Path

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._load_btn = QPushButton("Load Model...")
        self._load_btn.clicked.connect(self._on_load)
        layout.addRow(self._load_btn)

        self._name_lbl = QLabel("(no model)")
        self._verts_lbl = QLabel("-")
        self._faces_lbl = QLabel("-")
        self._extents_lbl = QLabel("-")
        self._watertight_lbl = QLabel("-")

        layout.addRow("File:", self._name_lbl)
        layout.addRow("Vertices:", self._verts_lbl)
        layout.addRow("Faces:", self._faces_lbl)
        layout.addRow("Extents:", self._extents_lbl)
        layout.addRow("Watertight:", self._watertight_lbl)

    def set_loading(self, loading: bool) -> None:
        """Disable the load button and show a spinner-style label while busy."""
        self._load_btn.setEnabled(not loading)
        self._load_btn.setText("Loading…" if loading else "Load Model...")

    def update_model(self, model) -> None:
        """Populate the info labels from a fully-loaded MeshModel."""
        self._name_lbl.setText(model.source_path.name)
        self._verts_lbl.setText(f"{len(model.mesh.vertices):,}")
        self._faces_lbl.setText(f"{len(model.mesh.faces):,}")
        ext = model.extents
        self._extents_lbl.setText(
            f"{float(ext[0]):.3f} x {float(ext[1]):.3f} x {float(ext[2]):.3f}"
        )
        wt = model.mesh.is_watertight
        suffix = " (repaired)" if model.was_repaired else ""
        self._watertight_lbl.setText(("Yes" if wt else "No") + suffix)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load 3D Model",
            "",
            "3D Models (*.stl *.STL *.obj *.OBJ *.ply *.PLY "
            "*.glb *.GLB *.gltf *.GLTF *.3mf *.3MF);;All Files (*)",
        )
        if path:
            self.load_requested.emit(Path(path))
