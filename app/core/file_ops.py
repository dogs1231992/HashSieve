# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

try:
    from send2trash import send2trash as _send2trash
    SEND2TRASH_AVAILABLE = True
except Exception:
    SEND2TRASH_AVAILABLE = False
    def _send2trash(path: str) -> None:  # type: ignore
        raise RuntimeError("send2trash is not installed")


@dataclass
class DeleteFailure:
    path: str
    message: str


def delete_files(paths: List[str], use_recycle_bin: bool = True) -> Tuple[List[str], List[DeleteFailure]]:
    succeeded: List[str] = []
    failed: List[DeleteFailure] = []
    for path in paths:
        try:
            if use_recycle_bin:
                _send2trash(path)
            else:
                os.remove(path)
            succeeded.append(path)
        except Exception as exc:
            failed.append(DeleteFailure(path=path, message=str(exc)))
    return succeeded, failed


def open_containing_folder(path: str) -> None:
    """Open the containing folder and, when supported, select the target file.

    Windows Explorer is sensitive to the exact /select argument format. Passing
    `/select,"C:/..."` as an already-quoted argument can be parsed incorrectly by
    Explorer on some systems and may open Documents/Desktop instead of selecting
    the file. Use one unquoted /select,<path> argument and let subprocess quote it.
    """
    target = Path(path)
    try:
        if sys.platform.startswith("win"):
            target_str = os.path.normpath(str(target))
            if target.exists():
                subprocess.Popen(["explorer.exe", f"/select,{target_str}"])
            else:
                parent = target.parent if target.parent.exists() else Path.home()
                subprocess.Popen(["explorer.exe", os.path.normpath(str(parent))])
        elif sys.platform == "darwin":
            if target.exists():
                subprocess.Popen(["open", "-R", str(target)])
            else:
                subprocess.Popen(["open", str(target.parent)])
        else:
            subprocess.Popen(["xdg-open", str(target.parent if target.parent.exists() else Path.home())])
    except Exception:
        pass
