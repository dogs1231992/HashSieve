# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Callable, Iterable, List


@dataclass
class ScanError:
    path: str
    message: str


@dataclass
class ScannedFile:
    path: Path
    key: str
    size: int = 0
    error: str = ""


def normalize_path(path: Path) -> str:
    try:
        return os.path.normcase(str(path.resolve()))
    except Exception:
        return os.path.normcase(str(path.absolute()))


def is_hidden(path: Path) -> bool:
    if path.name.startswith("."):
        return True
    if os.name == "nt":
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
    input_paths: Iterable[str | Path],
    *,
    follow_symlinks: bool = False,
    include_hidden: bool = False,
    should_cancel: Callable[[], bool] | None = None,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> tuple[List[ScannedFile], List[ScanError]]:
    files: List[ScannedFile] = []
    errors: List[ScanError] = []
    seen: set[str] = set()
    visited_dirs: set[str] = set()
    total_bytes = 0
    last_emit = 0.0

    def cancelled() -> bool:
        return bool(should_cancel and should_cancel())

    def emit(path_text: str, force: bool = False) -> None:
        nonlocal last_emit
        if on_progress is None:
            return
        now = monotonic()
        if force or now - last_emit >= 0.20:
            last_emit = now
            try:
                on_progress(len(files), total_bytes, path_text)
            except Exception:
                pass

    def add_file(p: Path) -> None:
        nonlocal total_bytes
        if cancelled():
            return
        try:
            if not p.is_file():
                return
            if not include_hidden and is_hidden(p):
                return
            key = normalize_path(p)
            if key in seen:
                return
            seen.add(key)
            size = 0
            err = ""
            try:
                size = int(p.stat().st_size)
            except Exception as exc:
                err = str(exc)
            files.append(ScannedFile(path=p, key=key, size=size, error=err))
            total_bytes += max(0, size)
            emit(str(p))
        except Exception as exc:
            errors.append(ScanError(str(p), str(exc)))

    for raw in input_paths:
        if cancelled():
            break
        p = Path(raw)
        try:
            if not p.exists():
                errors.append(ScanError(str(p), "Path does not exist"))
                continue
            if not include_hidden and is_hidden(p):
                continue
            if p.is_file():
                add_file(p)
            elif p.is_dir():
                for root, dirs, names in os.walk(p, followlinks=follow_symlinks):
                    if cancelled():
                        break
                    root_path = Path(root)
                    # os.walk(followlinks=True) can otherwise recurse forever when
                    # a symbolic link points back to an ancestor directory.
                    root_key = normalize_path(root_path)
                    if root_key in visited_dirs:
                        dirs[:] = []
                        continue
                    visited_dirs.add(root_key)
                    if not include_hidden:
                        dirs[:] = [d for d in dirs if not is_hidden(root_path / d)]
                    dirs.sort()
                    for name in sorted(names):
                        if cancelled():
                            break
                        add_file(root_path / name)
        except Exception as exc:
            errors.append(ScanError(str(p), str(exc)))
    emit("", force=True)
    return files, errors
