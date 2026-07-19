# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

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
class FileRecord:
    path: str
    filename: str = ""
    directory: str = ""
    extension: str = ""
    size: int = 0
    modified_time: str = ""
    created_time: str = ""
    hash_start_time: str = ""
    hash_end_time: str = ""
    duration_seconds: float = 0.0
    hashes: Dict[str, str] = field(default_factory=dict)
    error: str = ""
    group_id: int = 0
    duplicate_count: int = 1
    is_duplicate: bool = False

    def duplicate_key(self):
        return (self.size,) + tuple(self.hashes.get(k, "") for k in HASH_COLUMNS)

    def to_dict(self) -> dict:
        d = {
            "group_id": self.group_id if self.is_duplicate else "",
            "duplicate_count": self.duplicate_count if self.is_duplicate else "",
            "is_duplicate": self.is_duplicate,
            "filename": self.filename,
            "directory": self.directory,
            "extension": self.extension,
            "size": self.size,
            "modified_time": self.modified_time,
            "created_time": self.created_time,
            "hash_start_time": self.hash_start_time,
            "hash_end_time": self.hash_end_time,
            "duration_seconds": self.duration_seconds,
            "path": self.path,
            "error": self.error,
        }
        d.update(self.hashes)
        return d
