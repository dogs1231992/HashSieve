# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path
from typing import List

from PySide6.QtCore import QThread, Signal

from ..core.duplicate_finder import annotate_groups
from ..core.hasher import HashCancelled, compute_all_hashes
from ..core.models import FileRecord
from ..core.scanner import ScanError, ScannedFile, normalize_path, scan_paths


class HashWorker(QThread):
    scan_progress = Signal(int, int, str)  # count, bytes, path
    hash_progress = Signal(int, int, int, int, float, float)  # done, total, bytes_done, bytes_total, fps, bps
    phase_message = Signal(str)
    finished_all = Signal(list, list, bool, float)  # records, errors, cancelled, elapsed
    failed = Signal(str)

    def __init__(
        self,
        paths: List[str],
        *,
        follow_symlinks: bool = False,
        include_hidden: bool = False,
        ignore_empty_grouping: bool = True,
        max_workers: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self.paths = list(paths)
        self.follow_symlinks = follow_symlinks
        self.include_hidden = include_hidden
        self.ignore_empty_grouping = ignore_empty_grouping
        self.max_workers = min(max(1, int(os.cpu_count() or 1)), max(1, int(max_workers or 1)))
        self._cancelled = False
        self._lock = threading.Lock()
        self._done = 0
        self._bytes_done = 0
        self._last_emit = 0.0
        self._start_hash = 0.0

    def cancel(self) -> None:
        self._cancelled = True

    def _is_cancelled(self) -> bool:
        return self._cancelled

    def _add_bytes(self, n: int, total_files: int, total_bytes: int) -> None:
        with self._lock:
            self._bytes_done = min(total_bytes, self._bytes_done + max(0, int(n)))
            self._emit_hash_progress_locked(total_files, total_bytes)

    def _emit_hash_progress_locked(self, total_files: int, total_bytes: int, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self._last_emit < 0.20:
            return
        self._last_emit = now
        elapsed = max(0.001, now - self._start_hash)
        fps = self._done / elapsed
        bps = self._bytes_done / elapsed
        self.hash_progress.emit(self._done, total_files, self._bytes_done, total_bytes, fps, bps)

    def _hash_worker_loop(self, work_q: queue.Queue, results: list, errors: list, total_files: int, total_bytes: int) -> None:
        while not self._cancelled:
            try:
                item: ScannedFile | None = work_q.get_nowait()
            except queue.Empty:
                return
            if item is None:
                return
            try:
                rec = compute_all_hashes(
                    item.path,
                    should_cancel=self._is_cancelled,
                    on_bytes=lambda n, tf=total_files, tb=total_bytes: self._add_bytes(n, tf, tb),
                )
                results.append(rec)
            except HashCancelled:
                return
            except Exception as exc:
                errors.append(ScanError(str(item.path), str(exc)))
            finally:
                with self._lock:
                    self._done += 1
                    self._bytes_done = min(total_bytes, self._bytes_done)
                    self._emit_hash_progress_locked(total_files, total_bytes, force=True)
                work_q.task_done()

    def run(self) -> None:
        start = time.time()
        try:
            files, errors = scan_paths(
                self.paths,
                follow_symlinks=self.follow_symlinks,
                include_hidden=self.include_hidden,
                should_cancel=self._is_cancelled,
                on_progress=lambda c, b, p: self.scan_progress.emit(c, b, p),
            )
            if self._cancelled:
                self.finished_all.emit([], errors, True, time.time() - start)
                return
            total_files = len(files)
            total_bytes = sum(max(0, f.size) for f in files)
            if total_files == 0:
                self.finished_all.emit([], errors, False, time.time() - start)
                return
            self._start_hash = time.monotonic()
            self._last_emit = 0.0
            work_q: queue.Queue = queue.Queue()
            for item in files:
                work_q.put(item)
            results: list[FileRecord] = []
            threads = []
            for _ in range(min(self.max_workers, total_files)):
                th = threading.Thread(target=self._hash_worker_loop, args=(work_q, results, errors, total_files, total_bytes), daemon=True)
                threads.append(th)
                th.start()
            while any(th.is_alive() for th in threads):
                if self._cancelled:
                    break
                time.sleep(0.05)
            for th in threads:
                th.join()
            # Thread completion order is nondeterministic. Restore scan order so
            # the "keep first file" strategy always keeps the same file.
            scan_order = {item.key: index for index, item in enumerate(files)}
            results.sort(key=lambda rec: scan_order.get(normalize_path(Path(rec.path)), len(scan_order)))
            annotate_groups(results, ignore_empty_grouping=self.ignore_empty_grouping)
            self.finished_all.emit(results, errors, self._cancelled, time.time() - start)
        except Exception as exc:
            self.failed.emit(str(exc))
