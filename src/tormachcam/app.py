"""QApplication bootstrap for the desktop GUI."""

from __future__ import annotations

import sys


def launch_gui() -> int:
    """Start the PyQt6 GUI application.  Returns exit code."""
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        print(
            "PyQt6 is not installed.  Install the 'gui' extras:\n"
            "  pip install tormachcam[gui]",
            file=sys.stderr,
        )
        return 1

    from .gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("TormachCAM")
    app.setOrganizationName("TormachCAM")

    window = MainWindow()
    window.show()

    return app.exec()
