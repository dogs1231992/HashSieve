# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Literal

from .models import FileRecord

KeepStrategy = Literal["first", "oldest", "newest", "shortest_path", "longest_path"]
VALID_STRATEGIES = ("first", "oldest", "newest", "shortest_path", "longest_path")


def annotate_groups(records: List[FileRecord], *, ignore_empty_grouping: bool = True) -> List[FileRecord]:
    for rec in records:
        rec.group_id = 0
        rec.duplicate_count = 1
        rec.is_duplicate = False
    groups: Dict[tuple, List[FileRecord]] = defaultdict(list)
    for rec in records:
        if rec.error or not rec.hashes:
            continue
        if ignore_empty_grouping and rec.size == 0:
            continue
        groups[rec.duplicate_key()].append(rec)
    dup_groups = [members for key, members in sorted(groups.items(), key=lambda item: (item[0][0], item[0][1:])) if len(members) > 1]
    for group_id, members in enumerate(dup_groups, start=1):
        for rec in members:
            rec.group_id = group_id
            rec.duplicate_count = len(members)
            rec.is_duplicate = True
    return records


def get_duplicate_groups(records: Iterable[FileRecord]) -> Dict[int, List[FileRecord]]:
    grouped: Dict[int, List[FileRecord]] = defaultdict(list)
    for rec in records:
        if rec.is_duplicate and rec.group_id:
            grouped[rec.group_id].append(rec)
    return dict(grouped)


def choose_files_to_delete(records: List[FileRecord], strategy: KeepStrategy = "first") -> List[FileRecord]:
    if strategy not in VALID_STRATEGIES:
        strategy = "first"  # type: ignore[assignment]
    out: List[FileRecord] = []
    for _gid, members in sorted(get_duplicate_groups(records).items()):
        if strategy == "oldest":
            ordered = sorted(members, key=lambda r: r.modified_time or "")
        elif strategy == "newest":
            ordered = sorted(members, key=lambda r: r.modified_time or "", reverse=True)
        elif strategy == "shortest_path":
            ordered = sorted(members, key=lambda r: len(r.path))
        elif strategy == "longest_path":
            ordered = sorted(members, key=lambda r: len(r.path), reverse=True)
        else:
            ordered = list(members)
        out.extend(ordered[1:])
    return out


def summarize(records: List[FileRecord]) -> dict:
    groups = get_duplicate_groups(records)
    dup_files = sum(len(members) for members in groups.values())
    reclaimable = sum(r.size for r in choose_files_to_delete(records, "first"))
    return {
        "total_files": len(records),
        "total_size": sum(max(0, r.size) for r in records),
        "duplicate_group_count": len(groups),
        "duplicate_file_count": dup_files,
        "reclaimable_space": reclaimable,
    }
