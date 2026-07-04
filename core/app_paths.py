from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "HashSieve"
APP_VERSION = "v1.2026.07.04"
AUTHOR = "Shih-Han Wang"
AUTHOR_EMAIL = "wangsh@vt.edu"
GITHUB_URL = "https://github.com/dogs1231992/HashSieve"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/dogs1231992/HashSieve/main/VERSION.json"
SPONSOR_URL = "https://github.com/sponsors/dogs1231992"
BUYMEACOFFEE_URL = "https://buymeacoffee.com/dogs1231992"


def _base_env(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    if value:
        return Path(value)
    return fallback


def app_config_dir() -> Path:
    base = _base_env("APPDATA", Path.home() / ".config")
    return base / APP_NAME


def app_local_dir() -> Path:
    base = _base_env("LOCALAPPDATA", Path.home() / ".local" / "share")
    return base / APP_NAME


def log_dir() -> Path:
    return app_local_dir() / "Logs"



def settings_file() -> Path:
    return app_config_dir() / "settings.json"


def resource_path(relative: str) -> Path:
    """Return a project/PyInstaller friendly resource path."""
    import sys

    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    return Path(__file__).resolve().parents[1] / relative
