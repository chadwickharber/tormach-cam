"""QApplication bootstrap for the desktop GUI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def _setup_logging() -> None:
    log_path = Path.home() / ".tormachcam" / "app.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logging.getLogger(__name__).info("TormachCAM starting — log: %s", log_path)


def launch_gui() -> int:
    """Start the PyQt6 GUI application.  Returns exit code."""
    _setup_logging()
    log = logging.getLogger(__name__)

    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print(
            "PyQt6 is not installed.  Install the 'gui' extras:\n"
            "  pip install tormachcam[gui]",
            file=sys.stderr,
        )
        return 1

    log.info("Creating QApplication")
    from .gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("TormachCAM")
    app.setOrganizationName("TormachCAM")

    log.info("Creating MainWindow")
    window = MainWindow()
    window.show()
    log.info("Window shown — entering event loop")

    return app.exec()
