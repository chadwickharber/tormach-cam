"""G-code preview and export panel."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GCodePanel(QWidget):
    """Panel showing G-code preview with a save button."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Status bar
        self._status_lbl = QLabel("No toolpath computed.")
        layout.addWidget(self._status_lbl)

        # Text viewer
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        mono = QFont("Courier New", 9)
        mono.setFixedPitch(True)
        self._text.setFont(mono)
        layout.addWidget(self._text)

        # Buttons
        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save .ngc...")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        btn_layout.addStretch()
        btn_layout.addWidget(self._save_btn)
        layout.addLayout(btn_layout)

        self._lines: list[str] = []

    def set_gcode(self, lines: list[str]) -> None:
        self._lines = lines
        self._text.setPlainText("\n".join(lines))
        self._status_lbl.setText(f"{len(lines)} lines")
        self._save_btn.setEnabled(True)

    def clear(self) -> None:
        self._lines = []
        self._text.clear()
        self._status_lbl.setText("No toolpath computed.")
        self._save_btn.setEnabled(False)

    def _on_save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save G-code",
            "",
            "NGC Files (*.ngc);;All Files (*)",
        )
        if path:
            Path(path).write_text("\n".join(self._lines) + "\n")
