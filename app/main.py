from __future__ import annotations

import os
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow
from app.ui.theme import stylesheet


def main() -> int:
    cli_args = os.environ.get("PDF2_CLI")
    if cli_args:
        from app.cli import main as cli_main

        return cli_main(cli_args.split())

    app = QApplication(sys.argv)
    app.setApplicationName("Pdf2")
    app.setOrganizationName("Pdf2")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet(stylesheet())

    window = MainWindow()
    window.show()

    if os.environ.get("PDF2_SMOKE"):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(2000, app.quit)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
