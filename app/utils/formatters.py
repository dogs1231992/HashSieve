# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as _dt


def format_size(size: int | float) -> str:
    value = float(size or 0)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if value < 1024 or unit == "PB":
            if unit == "B":
                return f"{int(value):,} {unit}"
            return f"{value:,.2f} {unit}"
        value /= 1024
    return f"{value:,.2f} PB"


def format_datetime(ts: float | int | str | None) -> str:
    if ts in (None, ""):
        return ""
    if isinstance(ts, str):
        return ts
    try:
        return _dt.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def format_duration(seconds: float | int | None) -> str:
    try:
        return f"{float(seconds):.3f} s"
    except Exception:
        return ""
