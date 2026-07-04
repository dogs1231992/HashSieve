from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from .app_paths import settings_file, APP_VERSION

PREFERENCES_VERSION = APP_VERSION
# Increment this only when saved preferences are no longer compatible with the current defaults.
# New settings can usually be merged without a schema reset.
PREFERENCES_SCHEMA_VERSION = 1


def default_worker_count() -> int:
    return max(1, min(64, (os.cpu_count() or 1) - 2))


def default_column_order() -> list[str]:
    return [
        "group",
        "filename",
        "size_human",
        "md5",
        "sha1",
        "crc32",
        "sha256",
        "sha384",
        "sha512",
        "extension",
        "modified_time",
        "created_time",
        "duration",
        "path",
        "error",
    ]


@dataclass
class Preferences:
    language: str = "en-US"
    theme: str = "light"
    duplicate_algorithm: str = "all"
    workers: int = default_worker_count()
    worker_default_version: str = PREFERENCES_VERSION
    recycle_bin: bool = True
    follow_symlinks: bool = False
    include_hidden: bool = False
    preferences_schema_version: int = PREFERENCES_SCHEMA_VERSION
    ignore_empty_files_for_groups: bool = True
    last_export_dir: str = ""
    window_geometry: str = "1500x900"
    column_order: list[str] = field(default_factory=default_column_order)
    column_widths: dict[str, int] = field(default_factory=dict)
    sort_column: str = ""
    sort_reverse: bool = False

    @classmethod
    def defaults(cls) -> "Preferences":
        prefs = cls()
        prefs.workers = default_worker_count()
        prefs.worker_default_version = PREFERENCES_VERSION
        prefs.duplicate_algorithm = "all"
        prefs.include_hidden = False
        prefs.ignore_empty_files_for_groups = True
        prefs.preferences_schema_version = PREFERENCES_SCHEMA_VERSION
        prefs.column_order = default_column_order()
        prefs.column_widths = {}
        prefs.sort_column = ""
        prefs.sort_reverse = False
        return prefs

    @classmethod
    def load(cls) -> "Preferences":
        path = settings_file()
        if not path.exists():
            return cls.defaults()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))

            # Preference policy:
            # - preference_schema_version changes only when saved preferences are incompatible
            #   with current defaults or a default must be reset safely.
            # - If the schema differs, reset to current defaults instead of stacking one-off
            #   migrations forever.
            # - If the schema matches, merge known keys and ignore unknown keys.
            if int(data.get("preferences_schema_version", 0) or 0) != PREFERENCES_SCHEMA_VERSION:
                return cls.defaults()

            valid = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
            filtered = {k: v for k, v in data.items() if k in valid}
            prefs = cls(**filtered)
            if data.get("worker_default_version") != PREFERENCES_VERSION:
                prefs.workers = default_worker_count()
                prefs.worker_default_version = PREFERENCES_VERSION
            else:
                prefs.workers = max(1, min(64, int(prefs.workers)))
            prefs.duplicate_algorithm = "all"
            prefs.preferences_schema_version = PREFERENCES_SCHEMA_VERSION
            if prefs.theme not in {"light", "dark"}:
                prefs.theme = "light"
            if prefs.language is None:
                prefs.language = "en-US"
            valid_cols = default_column_order()
            prefs.column_order = [c for c in (prefs.column_order or []) if c in valid_cols]
            for c in valid_cols:
                if c not in prefs.column_order:
                    prefs.column_order.append(c)
            if not isinstance(prefs.column_widths, dict):
                prefs.column_widths = {}
            prefs.column_widths = {str(k): max(40, int(v)) for k, v in prefs.column_widths.items() if str(k) in valid_cols}
            if prefs.sort_column not in valid_cols:
                prefs.sort_column = ""
            prefs.sort_reverse = bool(prefs.sort_reverse)
            prefs.include_hidden = bool(getattr(prefs, "include_hidden", False))
            prefs.follow_symlinks = bool(getattr(prefs, "follow_symlinks", False))
            prefs.recycle_bin = bool(getattr(prefs, "recycle_bin", True))
            prefs.ignore_empty_files_for_groups = bool(getattr(prefs, "ignore_empty_files_for_groups", True))
            return prefs
        except Exception:
            return cls.defaults()

    def save(self) -> None:
        path = settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
