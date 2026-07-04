from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox

try:
    from tkinterdnd2 import TkinterDnD  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    TkinterDnD = None

from core.app_logging import setup_logging
from core.app_paths import APP_NAME
from gui.app import HashSieveApp


def main() -> None:
    log_file = setup_logging()
    logging.getLogger(__name__).info("Starting %s", APP_NAME)
    try:
        if TkinterDnD is not None:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
        app = HashSieveApp(root, log_file=log_file)
        root.mainloop()
    except Exception as exc:
        logging.getLogger(__name__).exception("Fatal application error")
        try:
            messagebox.showerror(APP_NAME, f"Fatal error:\n{exc}\n\nSee log file:\n{log_file}")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
