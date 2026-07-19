# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication
except ImportError as exc:
    print("=" * 72)
    print("HashSieve cannot load PySide6 / Qt.")
    print()
    print("This is usually caused by a broken or mixed Qt/PySide6 environment, ")
    print("especially when running from Anaconda base or after mixing conda and pip Qt packages.")
    print()
    print("Recommended fix:")
    print("  1. Close HashSieve.")
    print("  2. Run: run_conda_env.bat")
    print("     This creates an isolated conda environment named hashsieve-gui.")
    print()
    print("Alternative fix:")
    print("  Run: run_clean_venv.bat")
    print()
    print("Original import error:")
    print(f"  {type(exc).__name__}: {exc}")
    print("=" * 72)
    raise SystemExit(1) from exc

from app import config
from app.ui.main_window import MainWindow
from app.utils.app_logging import setup_logging
from app.utils.paths import get_assets_dir


def main() -> int:
    setup_logging()
    # Qt 6 enables high-DPI scaling by default. Avoid deprecated Qt 5 attributes
    # so users do not see noisy DeprecationWarning messages in the console.
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationDisplayName(config.APP_DISPLAY_NAME)
    app.setOrganizationName(config.AUTHOR_NAME)
    icon_path = get_assets_dir() / "hashsieve.ico"
    if not icon_path.exists():
        icon_path = get_assets_dir() / "hashsieve_logo.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
