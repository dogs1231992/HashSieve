# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from pathlib import Path

from .. import config


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", get_app_root()))
    return base / relative


def get_assets_dir() -> Path:
    return resource_path("assets")


def get_locales_dir() -> Path:
    return resource_path("app/i18n/locales")


def get_executable_dir() -> Path:
    return Path(sys.executable).resolve().parent if is_frozen() else get_app_root()


def get_user_data_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = str(Path.home() / "Library" / "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    path = Path(base) / config.APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_log_dir() -> Path:
    path = get_user_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
