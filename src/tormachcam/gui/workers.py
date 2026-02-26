"""QThread workers for background computation."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.job import Job
from ..core.toolpath.base import Toolpath


class ToolpathWorker(QThread):
    """Runs Job.compute_toolpaths() in a background thread.

    Signals
    -------
    finished(list[Toolpath]):
        Emitted when toolpath computation completes successfully.
    error(str):
        Emitted when an exception is raised during computation.
    progress(str):
        Emitted with a status message during processing.
    """

    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, job: Job, parent=None):
        super().__init__(parent)
        self._job = job

    def run(self) -> None:
        try:
            self.progress.emit("Slicing model...")
            toolpaths = self._job.compute_toolpaths()
            self.progress.emit(
                f"Done: {len(toolpaths)} operations, "
                f"{sum(t.total_points for t in toolpaths)} points"
            )
            self.finished.emit(toolpaths)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class LoadModelWorker(QThread):
    """Loads an STL file in a background thread."""

    finished = pyqtSignal(object)  # MeshModel
    error = pyqtSignal(str)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        from ..core.model import load_stl

        try:
            model = load_stl(self._path)
            self.finished.emit(model)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
