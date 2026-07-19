# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .paths import get_log_dir

SESSION_LOG_FILE: Path | None = None


def setup_logging() -> Path:
    global SESSION_LOG_FILE
    if SESSION_LOG_FILE is not None:
        return SESSION_LOG_FILE
    SESSION_LOG_FILE = get_log_dir() / f"HashSieve_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(SESSION_LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )
    logging.getLogger(__name__).info("HashSieve session log started: %s", SESSION_LOG_FILE)
    return SESSION_LOG_FILE


def get_session_log_file() -> Path | None:
    return SESSION_LOG_FILE
