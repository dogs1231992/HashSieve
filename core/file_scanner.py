from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Callable, Iterable


@dataclass
class ScannedFile:
    path: Path
    key: str
    name: str = ""
    extension: str = ""
    size: int = 0
    modified_time: str = ""
    created_time: str = ""
    error: str = ""


def normalize_path(path: Path) -> str:
    try:
        return os.path.normcase(str(path.resolve()))
    except Exception:
        return os.path.normcase(str(path.absolute()))


def _fmt_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _is_hidden(path: Path) -> bool:
    if path.name.startswith('.'):
        return True
    if os.name == 'nt':
        try:
            import ctypes
            attrs = ctypes.windll.kernel32.GetFileAttributesW(str(path))
            if attrs == -1:
                return False
            return bool(attrs & 0x2)
        except Exception:
            return False
    return False


def scan_paths(
    paths: Iterable[Path],
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = True,
    stop_event=None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[ScannedFile]:
    """Expand files/folders recursively and return each normalized file once.

    progress_callback receives (file_count, total_bytes, last_path). It is rate-limited
    so large folders do not flood the GUI event queue.
    """
    seen: set[str] = set()
    out: list[ScannedFile] = []
    scanned_count = 0
    scanned_bytes = 0
    last_emit = 0.0

    def stopped() -> bool:
        return bool(stop_event is not None and stop_event.is_set())

    def emit_progress(last_path: str, *, force: bool = False) -> None:
        nonlocal last_emit
        if progress_callback is None:
            return
        now = monotonic()
        if force or now - last_emit >= 0.20:
            last_emit = now
            try:
                progress_callback(scanned_count, scanned_bytes, last_path)
            except Exception:
                pass

    def add_file(file_path: Path) -> None:
        nonlocal scanned_count, scanned_bytes
        if stopped():
            return
        try:
            if not file_path.is_file():
                return
            if not include_hidden and _is_hidden(file_path):
                return
            key = normalize_path(file_path)
            if key in seen:
                return
            seen.add(key)
            item = ScannedFile(
                path=file_path,
                key=key,
                name=file_path.name,
                extension=file_path.suffix.lower(),
            )
            try:
                st = file_path.stat()
                item.size = int(st.st_size)
                item.modified_time = _fmt_ts(st.st_mtime)
                item.created_time = _fmt_ts(getattr(st, "st_ctime", 0))
            except Exception as exc:
                item.error = str(exc)
            out.append(item)
            scanned_count += 1
            scanned_bytes += max(0, item.size)
            emit_progress(str(file_path))
        except Exception:
            return

    for raw in paths:
        if stopped():
            break
        try:
            p = Path(raw)
            if not p.exists():
                continue
            if not include_hidden and _is_hidden(p):
                continue
            if p.is_file():
                add_file(p)
                continue
            if not p.is_dir():
                continue
            for root, dirs, files in os.walk(p, followlinks=follow_symlinks):
                if stopped():
                    break
                root_path = Path(root)
                if not include_hidden:
                    dirs[:] = [d for d in dirs if not _is_hidden(root_path / d)]
                for name in files:
                    if stopped():
                        break
                    add_file(root_path / name)
        except Exception:
            continue
    emit_progress("", force=True)
    return out


def walk_files(
    paths: Iterable[Path],
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = True,
) -> list[Path]:
    """Backward-compatible wrapper returning paths only."""
    return [item.path for item in scan_paths(paths, follow_symlinks=follow_symlinks, include_hidden=include_hidden)]
