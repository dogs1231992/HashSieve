from __future__ import annotations

import hashlib
import os
import zlib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable
from time import perf_counter

HASH_COLUMNS = ("md5", "sha1", "crc32", "sha256", "sha384", "sha512")
DISPLAY_NAMES = {
    "md5": "MD5",
    "sha1": "SHA-1",
    "crc32": "CRC32",
    "sha256": "SHA-256",
    "sha384": "SHA-384",
    "sha512": "SHA-512",
}


@dataclass
class FileHashResult:
    path: str
    name: str = ""
    extension: str = ""
    size: int = 0
    modified_time: str = ""
    created_time: str = ""
    hash_start_time: str = ""
    hash_end_time: str = ""
    duration_seconds: float = 0.0
    hashes: dict[str, str] = field(default_factory=dict)
    error: str = ""


def bytes_to_human(size: int | float) -> str:
    value = float(size)
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if value < 1024 or unit == "PB":
            if unit == "B":
                return f"{int(value):,} {unit}"
            return f"{value:,.2f} {unit}"
        value /= 1024
    return f"{value:,.2f} PB"


def _fmt_ts(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def compute_file_hashes(
    path: str,
    chunk_size: int = 8 * 1024 * 1024,
    progress_callback: Callable[[int], None] | None = None,
    progress_interval: int = 16 * 1024 * 1024,
) -> FileHashResult:
    p = Path(path)
    result = FileHashResult(path=str(p))
    result.name = p.name
    result.extension = p.suffix.lower()
    try:
        st = p.stat()
        result.size = int(st.st_size)
        result.modified_time = _fmt_ts(st.st_mtime)
        result.created_time = _fmt_ts(getattr(st, "st_ctime", 0))
    except Exception as exc:
        result.error = f"stat failed: {exc}"
        return result

    # hashlib on some Python builds supports usedforsecurity=False.
    # Use it when available so MD5 is treated only as a checksum, not a security primitive.
    try:
        md5 = hashlib.md5(usedforsecurity=False)  # type: ignore[call-arg]
    except TypeError:
        md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    sha384 = hashlib.sha384()
    sha512 = hashlib.sha512()
    crc = 0

    result.hash_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start = perf_counter()
    try:
        pending_progress = 0
        with open(p, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunk_len = len(chunk)
                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)
                sha384.update(chunk)
                sha512.update(chunk)
                crc = zlib.crc32(chunk, crc)
                pending_progress += chunk_len
                if progress_callback is not None and pending_progress >= progress_interval:
                    try:
                        progress_callback(pending_progress)
                    except Exception:
                        pass
                    pending_progress = 0
        if progress_callback is not None and pending_progress:
            try:
                progress_callback(pending_progress)
            except Exception:
                pass
        result.hashes = {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "crc32": f"{crc & 0xFFFFFFFF:08x}",
            "sha256": sha256.hexdigest(),
            "sha384": sha384.hexdigest(),
            "sha512": sha512.hexdigest(),
        }
    except Exception as exc:
        result.error = str(exc)
    finally:
        result.duration_seconds = perf_counter() - start
        result.hash_end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return result
