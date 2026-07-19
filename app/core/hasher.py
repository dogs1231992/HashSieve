# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import zlib
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Callable

from .models import FileRecord, HASH_COLUMNS

CHUNK_SIZE = 8 * 1024 * 1024


class HashCancelled(Exception):
    pass


def _fmt_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def compute_all_hashes(
    file_path: str | Path,
    *,
    should_cancel: Callable[[], bool] | None = None,
    on_bytes: Callable[[int], None] | None = None,
    progress_interval: int = 16 * 1024 * 1024,
) -> FileRecord:
    p = Path(file_path)
    rec = FileRecord(path=str(p), filename=p.name, directory=str(p.parent), extension=p.suffix.lower())
    try:
        st = p.stat()
        rec.size = int(st.st_size)
        rec.modified_time = _fmt_ts(st.st_mtime)
        rec.created_time = _fmt_ts(getattr(st, "st_ctime", 0))
    except Exception as exc:
        rec.error = f"stat failed: {exc}"
        return rec

    try:
        md5 = hashlib.md5(usedforsecurity=False)  # type: ignore[call-arg]
    except TypeError:
        md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    sha384 = hashlib.sha384()
    sha512 = hashlib.sha512()
    crc = 0

    rec.hash_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = perf_counter()
    pending = 0
    try:
        with open(p, "rb") as f:
            while True:
                if should_cancel and should_cancel():
                    raise HashCancelled(str(p))
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                n = len(chunk)
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
                sha384.update(chunk)
                sha512.update(chunk)
                crc = zlib.crc32(chunk, crc)
                pending += n
                if on_bytes and pending >= progress_interval:
                    on_bytes(pending)
                    pending = 0
        if on_bytes and pending:
            on_bytes(pending)
        rec.hashes = {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "crc32": f"{crc & 0xFFFFFFFF:08x}",
            "sha256": sha256.hexdigest(),
            "sha384": sha384.hexdigest(),
            "sha512": sha512.hexdigest(),
        }
        for k in HASH_COLUMNS:
            rec.hashes.setdefault(k, "")
    except HashCancelled:
        raise
    except Exception as exc:
        rec.error = str(exc)
    finally:
        rec.duration_seconds = perf_counter() - start
        rec.hash_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return rec
