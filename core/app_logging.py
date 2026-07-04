from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from .app_paths import APP_NAME, log_dir


def setup_logging() -> Path:
    folder = log_dir()
    folder.mkdir(parents=True, exist_ok=True)
    logfile = folder / f"{APP_NAME}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    root.addHandler(sh)

    logging.getLogger(__name__).info("Logging started: %s", logfile)
    return logfile
