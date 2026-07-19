# -*- coding: utf-8 -*-
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Dict

from .paths import get_user_data_dir

PREFERENCES_SCHEMA_VERSION = 3


def max_worker_count() -> int:
    """Return the maximum supported worker count for this machine.

    HashSieve uses Python threads for disk I/O and hashing.  The upper bound is
    the number of logical CPUs reported by the operating system so the GUI can
    never request more workers than the machine exposes.
    """
    return max(1, int(os.cpu_count() or 1))


def clamp_worker_count(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default_worker_count()
    return min(max_worker_count(), max(1, parsed))


def default_worker_count() -> int:
    return max(1, max_worker_count() - 2)


DEFAULT_SETTINGS: Dict[str, Any] = {
    "preferences_schema_version": PREFERENCES_SCHEMA_VERSION,
    "language": "en-US",
    "theme": "light",
    "follow_symlinks": False,
    "include_hidden": False,
    "ignore_empty_grouping": True,
    "use_recycle_bin": True,
    "workers": default_worker_count(),
    "last_export_dir": "",
    "window_width": 1320,
    "window_height": 820,
    "show_duplicates_only": False,
    "keep_strategy": "first",
    "sort_column": "group",
    "sort_reverse": False,
    "column_order": [],
    "column_widths": {},
}


def new_default_settings() -> Dict[str, Any]:
    """Return an isolated copy of the built-in defaults.

    The defaults contain mutable values such as ``column_order`` and
    ``column_widths``.  A deep copy prevents runtime changes from accidentally
    mutating the Python defaults that Restore Defaults must use as its source of
    truth.
    """
    defaults = copy.deepcopy(DEFAULT_SETTINGS)
    defaults["workers"] = clamp_worker_count(defaults.get("workers"))
    return defaults


def get_config_path() -> Path:
    return get_user_data_dir() / "settings.json"


class AppSettings:
    def __init__(self, config_path: Path | None = None):
        self.config_path = config_path or get_config_path()
        self._data: Dict[str, Any] = new_default_settings()
        self.load()

    def load(self) -> None:
        if not self.config_path.exists():
            return
        try:
            loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                self._data = new_default_settings()
                self.save()
                return
            if loaded.get("preferences_schema_version") != PREFERENCES_SCHEMA_VERSION:
                self._data = new_default_settings()
                self.save()
                return
            merged = new_default_settings()
            for k in DEFAULT_SETTINGS:
                if k in loaded:
                    merged[k] = loaded[k]
            merged["workers"] = clamp_worker_count(merged.get("workers"))
            self._data = merged
            if merged.get("workers") != loaded.get("workers"):
                self.save()
        except Exception:
            # Recover from a truncated/corrupt JSON file instead of repeating
            # the same parse failure on every launch.
            self._data = new_default_settings()
            self.save()

    def reset_defaults(self) -> None:
        self._data = new_default_settings()
        self.save()

    def save(self) -> None:
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        value = self._data.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))
        return copy.deepcopy(value)

    def as_dict(self) -> Dict[str, Any]:
        """Return a safe snapshot of the currently loaded preferences."""
        return copy.deepcopy(self._data)

    def set(self, key: str, value: Any) -> None:
        if key == "workers":
            value = clamp_worker_count(value)
        self._data[key] = copy.deepcopy(value)
        self.save()

    def set_many(self, values: Dict[str, Any]) -> None:
        normalized = copy.deepcopy(dict(values))
        if "workers" in normalized:
            normalized["workers"] = clamp_worker_count(normalized["workers"])
        self._data.update(normalized)
        self.save()
