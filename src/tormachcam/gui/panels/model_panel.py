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

from ...core.model import MeshModel


class ModelPanel(QWidget):
    """Displays model information and provides a load button."""

    model_loaded = pyqtSignal(object)  # MeshModel

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self._load_btn = QPushButton("Load STL...")
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

    def update_model(self, model: MeshModel) -> None:
        self._name_lbl.setText(model.source_path.name)
        self._verts_lbl.setText(str(len(model.mesh.vertices)))
        self._faces_lbl.setText(str(len(model.mesh.faces)))
        ext = model.extents
        self._extents_lbl.setText(
            f"{ext[0]:.3f} x {ext[1]:.3f} x {ext[2]:.3f}"
        )
        wt = model.mesh.is_watertight
        suffix = " (repaired)" if model.was_repaired else ""
        self._watertight_lbl.setText(("Yes" if wt else "No") + suffix)

    def _on_load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load STL File",
            "",
            "STL Files (*.stl *.STL);;All Files (*)",
        )
        if path:
            from ...core.model import load_stl

            model = load_stl(Path(path))
            self.update_model(model)
            self.model_loaded.emit(model)
