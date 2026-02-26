"""QThread workers for background computation."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from ..core.job import Job


class ToolpathWorker(QThread):
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
        except Exception as exc:
            self.error.emit(str(exc))


class LoadModelWorker(QThread):
    """Loads a mesh file in a background thread.

    Also pre-builds the decimated display mesh so the viewport receives
    a lightweight vertex/face array rather than the raw full-res mesh.
    """

    finished = pyqtSignal(object)   # MeshModel
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, path: Path, parent=None):
        super().__init__(parent)
        self._path = path

    def run(self) -> None:
        from ..core.model import load_mesh

        try:
            self.progress.emit(f"Loading {self._path.name}…")
            model = load_mesh(self._path)   # decimation pre-built inside
            self.finished.emit(model)
        except Exception as exc:
            self.error.emit(str(exc))


class PrevistaWarmupWorker(QThread):
    """Pre-imports pyvista/pyvistaqt in a background thread.

    Module-level imports (loading C extensions, reading shader files) are
    the slowest part of VTK startup.  By doing them off the main thread
    we ensure they're done before the user clicks Load, so the viewport
    widget creation is near-instant when it's actually needed.
    """

    done = pyqtSignal()

    def run(self) -> None:
        try:
            import pyvista  # noqa: F401
            import pyvistaqt  # noqa: F401
        except ImportError:
            pass
        self.done.emit()
