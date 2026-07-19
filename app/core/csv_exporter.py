# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .models import FileRecord, HASH_COLUMNS, DISPLAY_NAMES

COLUMNS = [
    ("group_id", "Group"),
    ("duplicate_count", "Duplicate Count"),
    ("is_duplicate", "Is Duplicate"),
    ("filename", "Filename"),
    ("size", "Size"),
] + [(k, DISPLAY_NAMES[k]) for k in HASH_COLUMNS] + [
    ("extension", "Extension"),
    ("modified_time", "Modified Time"),
    ("created_time", "Created Time"),
    ("hash_start_time", "Hash Start Time"),
    ("hash_end_time", "Hash End Time"),
    ("duration_seconds", "Hashing Duration Seconds"),
    ("directory", "Directory"),
    ("path", "Full Path"),
    ("error", "Error"),
]


def export_to_csv(records: Iterable[FileRecord], output_path: Path | str) -> int:
    records = list(records)
    output_path = Path(output_path)
    keys = [k for k, _ in COLUMNS]
    headers = [h for _, h in COLUMNS]
    with output_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writerow(dict(zip(keys, headers)))
        for rec in records:
            d = rec.to_dict()
            row = {k: d.get(k, "") for k in keys}
            writer.writerow(row)
    return len(records)
