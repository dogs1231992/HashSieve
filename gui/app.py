from __future__ import annotations

import csv
import json
import logging
import os
import platform
import queue
import subprocess
import sys
import threading
import traceback
import urllib.parse
import urllib.request
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from time import monotonic
from pathlib import Path
from typing import Callable, Iterable

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont

try:
    from tkinterdnd2 import DND_FILES  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    DND_FILES = None

try:
    from send2trash import send2trash  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    send2trash = None

from core.app_paths import (
    APP_NAME,
    APP_VERSION,
    AUTHOR,
    AUTHOR_EMAIL,
    BUYMEACOFFEE_URL,
    GITHUB_URL,
    UPDATE_VERSION_URL,
    SPONSOR_URL,
    log_dir,
    resource_path,
)
from core.file_scanner import ScannedFile, normalize_path, scan_paths
from core.hash_worker import DISPLAY_NAMES, HASH_COLUMNS, FileHashResult, bytes_to_human, compute_file_hashes
from core.i18n import SUPPORTED_LANGUAGES, Translator
from core.preferences import Preferences, default_worker_count

LOG = logging.getLogger(__name__)

LIGHT_THEME = {
    "bg": "#f8fafc",
    "surface": "#ffffff",
    "surface2": "#e2e8f0",
    "text": "#0f172a",
    "muted": "#64748b",
    "accent": "#2563eb",
    "accent_hover": "#1d4ed8",
    "danger": "#dc2626",
    "warning": "#b45309",
    "border": "#cbd5e1",
    "marked": "#fee2e2",
    "duplicate": "#eff6ff",
}

DARK_THEME = {
    "bg": "#0f172a",
    "surface": "#111827",
    "surface2": "#1f2937",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "accent": "#3b82f6",
    "accent_hover": "#60a5fa",
    "danger": "#f87171",
    "warning": "#fbbf24",
    "border": "#334155",
    "marked": "#7f1d1d",
    "duplicate": "#1e3a8a",
}

GROUP_COLORS_LIGHT = [
    "#e0f2fe",
    "#dcfce7",
    "#fef3c7",
    "#ede9fe",
    "#fce7f3",
    "#ccfbf1",
    "#dbeafe",
    "#fae8ff",
    "#e5e7eb",
    "#ffedd5",
]
GROUP_COLORS_DARK = [
    "#0c4a6e",
    "#14532d",
    "#713f12",
    "#4c1d95",
    "#831843",
    "#134e4a",
    "#1e3a8a",
    "#701a75",
    "#374151",
    "#7c2d12",
]


@dataclass
class FileEntry:
    path: Path
    key: str
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
    duplicate_group: int = 0

    def update_from_result(self, result: FileHashResult) -> None:
        self.name = result.name
        self.extension = result.extension
        self.size = result.size
        self.modified_time = result.modified_time
        self.created_time = result.created_time
        self.hash_start_time = result.hash_start_time
        self.hash_end_time = result.hash_end_time
        self.duration_seconds = result.duration_seconds
        self.hashes = dict(result.hashes)
        self.error = result.error


class HashSieveApp:
    def __init__(self, root: tk.Tk, log_file: Path | None = None) -> None:
        self.root = root
        self.log_file = log_file
        self.prefs = Preferences.load()
        self.translator = Translator(self.prefs.language)
        self.theme = DARK_THEME if self.prefs.theme == "dark" else LIGHT_THEME
        self.entries: dict[str, FileEntry] = {}
        self.order: list[str] = []
        self.displayed_keys: list[str] = []
        self.result_queue: queue.Queue = queue.Queue()
        self.stop_event = threading.Event()
        self.hash_thread: threading.Thread | None = None
        self.scan_thread: threading.Thread | None = None
        self.running = False
        self.scan_running = False
        self.scan_count = 0
        self.scan_bytes = 0
        self.last_progress_ui_update = 0.0
        self.done_count = 0
        self.total_to_hash = 0
        self.bytes_done = 0
        self.total_bytes_to_hash = 0
        self.hash_pending_after_run = False
        self.sort_column: str | None = self.prefs.sort_column or None
        self.sort_reverse = bool(self.prefs.sort_reverse)
        self.container: tk.Frame | None = None
        self.widgets: dict[str, object] = {}
        self.last_status = ""
        self.hash_start_monotonic = 0.0
        self.hash_last_rate_time = 0.0
        self.hash_last_rate_done = 0
        self.hash_last_rate_bytes = 0
        self.update_checked = False
        self.header_drag_col: str | None = None
        self.header_drag_start_x = 0

        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry(self.prefs.window_geometry or "1500x900")
        self.root.minsize(1180, 720)
        self.root.configure(bg=self.theme["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.set_window_icon()
        self.build_ui()
        self.poll_queue()
        self.root.after(1500, self.check_for_updates_silent)
        self.set_status(self.t("Ready. Drag files or folders into the window, or use Add Files / Add Folder."))

    def t(self, key: str, fallback: str | None = None) -> str:
        return self.translator.t(key, fallback)

    def set_window_icon(self) -> None:
        """Set the runtime window icon. PyInstaller's icon controls the EXE icon only; Tk still needs this."""
        try:
            ico = resource_path("assets/hashsieve.ico")
            if os.name == "nt" and ico.exists():
                self.root.iconbitmap(default=str(ico))
                return
        except Exception as exc:
            LOG.debug("iconbitmap failed: %r", exc)
        try:
            png = resource_path("assets/hashsieve_logo.png")
            if png.exists():
                self._window_icon_photo = tk.PhotoImage(file=str(png))
                self.root.iconphoto(True, self._window_icon_photo)
        except Exception as exc:
            LOG.debug("iconphoto failed: %r", exc)

    def min_column_width(self, col: str) -> int:
        try:
            font = tkfont.nametofont("TkDefaultFont")
            heading = getattr(self, "column_headings", {}).get(col, col)
            return max(70, font.measure(str(heading)) + 34)
        except Exception:
            return 70

    def save_column_state(self) -> None:
        if not hasattr(self, "tree"):
            return
        try:
            display = list(self.tree["displaycolumns"])
            if display and display != ["#all"]:
                self.prefs.column_order = [str(c) for c in display if str(c) in getattr(self, "all_columns", [])]
            self.prefs.column_widths = {col: int(self.tree.column(col, "width")) for col in getattr(self, "all_columns", [])}
            self.prefs.save()
        except Exception as exc:
            LOG.debug("save_column_state failed: %r", exc)

    def auto_fit_column(self, col: str) -> None:
        if not hasattr(self, "tree") or col not in getattr(self, "all_columns", []):
            return
        try:
            font = tkfont.nametofont("TkDefaultFont")
            heading_font = tkfont.nametofont("TkHeadingFont") if "TkHeadingFont" in tkfont.names() else font
            width = max(self.min_column_width(col), heading_font.measure(str(self.column_headings.get(col, col))) + 34)
            # Only measure currently visible rows. This keeps auto-fit responsive even for very large scans.
            for item in self.tree.get_children(""):
                value = self.tree.set(item, col)
                width = max(width, font.measure(str(value)) + 28)
            width = min(width, 2200)
            self.tree.column(col, width=width, minwidth=self.min_column_width(col), stretch=False)
            self.save_column_state()
            self.set_status(self.t("Column width adjusted: {column}").format(column=self.column_headings.get(col, col)))
        except Exception as exc:
            LOG.debug("auto_fit_column failed: %r", exc)

    def on_tree_button_press(self, event) -> None:
        self.header_drag_col = None
        self.header_drag_start_x = int(getattr(event, "x", 0))
        try:
            region = self.tree.identify_region(event.x, event.y)
            if region == "heading":
                col_id = self.tree.identify_column(event.x)
                col = self.column_from_tree_id(col_id)
                if col:
                    self.header_drag_col = col
        except Exception:
            pass

    def on_tree_button_release(self, event) -> None:
        try:
            # Always save widths after mouse release; this captures native Treeview separator resizing.
            source = self.header_drag_col
            region = self.tree.identify_region(event.x, event.y)
            target = self.column_from_tree_id(self.tree.identify_column(event.x))
            moved = abs(int(getattr(event, "x", 0)) - self.header_drag_start_x) > 8
            if source and target and source != target and moved and region == "heading":
                cols = list(self.tree["displaycolumns"])
                if source in cols and target in cols:
                    i, j = cols.index(source), cols.index(target)
                    cols[i], cols[j] = cols[j], cols[i]
                    self.tree["displaycolumns"] = tuple(cols)
                    self.prefs.column_order = cols
                    self.set_status(self.t("Column order saved."))
            self.save_column_state()
        except Exception as exc:
            LOG.debug("on_tree_button_release failed: %r", exc)
        finally:
            self.header_drag_col = None

    def column_from_tree_id(self, col_id: str) -> str | None:
        try:
            if not col_id or not col_id.startswith("#"):
                return None
            index = int(col_id[1:]) - 1
            display = list(self.tree["displaycolumns"])
            if not display or display == ["#all"]:
                display = list(getattr(self, "columns", []))
            if 0 <= index < len(display):
                return str(display[index])
        except Exception:
            return None
        return None

    def build_ui(self) -> None:
        self.theme = DARK_THEME if self.prefs.theme == "dark" else LIGHT_THEME
        self.root.configure(bg=self.theme["bg"])
        self._configure_styles()
        self._build_menu()

        if self.container is not None:
            self.container.destroy()
        self.widgets.clear()

        root = tk.Frame(self.root, bg=self.theme["bg"])
        root.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)
        self.container = root
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(3, weight=1)

        title_row = tk.Frame(root, bg=self.theme["bg"])
        title_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        title_row.grid_columnconfigure(0, weight=1)
        tk.Label(
            title_row,
            text=self.t("HashSieve — recursive hash and duplicate-file cleaner"),
            bg=self.theme["bg"],
            fg=self.theme["text"],
            font=("Segoe UI", 18, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")
        tk.Label(
            title_row,
            text=self.t("Drop files/folders here. Folders are scanned recursively."),
            bg=self.theme["bg"],
            fg=self.theme["muted"],
            font=("Segoe UI", 10),
            anchor="e",
        ).grid(row=0, column=1, sticky="e")

        toolbar = tk.Frame(root, bg=self.theme["surface"], highlightbackground=self.theme["border"], highlightthickness=1)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        for i in range(16):
            toolbar.grid_columnconfigure(i, weight=0)
        toolbar.grid_columnconfigure(15, weight=1)

        self.add_files_button = self._button(toolbar, "Add Files", self.add_files)
        self.add_files_button.grid(row=0, column=0, padx=(10, 4), pady=8)
        self.add_folder_button = self._button(toolbar, "Add Folder", self.add_folder)
        self.add_folder_button.grid(row=0, column=1, padx=4, pady=8)
        self.clear_button = self._button(toolbar, "Clear List", self.clear_all)
        self.clear_button.grid(row=0, column=2, padx=4, pady=8)
        self.stop_button = self._button(toolbar, "Stop", self.stop_hashing, danger=True)
        self.stop_button.grid(row=0, column=3, padx=(14, 4), pady=8)
        self.export_button = self._button(toolbar, "Export CSV", self.export_csv)
        self.export_button.grid(row=0, column=4, padx=(14, 4), pady=8)

        tk.Label(toolbar, text=self.t("Workers:"), bg=self.theme["surface"], fg=self.theme["text"], font=("Segoe UI", 10)).grid(row=0, column=5, padx=(14, 4), pady=8)
        self.workers_var = tk.IntVar(value=int(self.prefs.workers))
        tk.Spinbox(toolbar, from_=1, to=64, textvariable=self.workers_var, width=4, command=self.on_workers_changed).grid(row=0, column=6, padx=4, pady=8)

        tk.Label(toolbar, text=self.t("Duplicate rule: size + all hashes"), bg=self.theme["surface"], fg=self.theme["muted"], font=("Segoe UI", 10)).grid(row=0, column=7, padx=(14, 4), pady=8)

        self.recycle_var = tk.BooleanVar(value=bool(self.prefs.recycle_bin))
        tk.Checkbutton(
            toolbar,
            text=self.t("Recycle bin"),
            variable=self.recycle_var,
            command=self.on_recycle_changed,
            bg=self.theme["surface"],
            fg=self.theme["text"],
            selectcolor=self.theme["surface2"],
            activebackground=self.theme["surface"],
            activeforeground=self.theme["text"],
        ).grid(row=0, column=8, padx=(10, 4), pady=8)

        self.duplicates_only_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            toolbar,
            text=self.t("Duplicates only"),
            variable=self.duplicates_only_var,
            command=self.refresh_tree,
            bg=self.theme["surface"],
            fg=self.theme["text"],
            selectcolor=self.theme["surface2"],
            activebackground=self.theme["surface"],
            activeforeground=self.theme["text"],
        ).grid(row=0, column=9, padx=(10, 4), pady=8)

        filter_row = tk.Frame(root, bg=self.theme["bg"])
        filter_row.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        filter_row.grid_columnconfigure(1, weight=1)
        tk.Label(filter_row, text=self.t("Search/filter:"), bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.search_var = tk.StringVar(value="")
        search_entry = tk.Entry(filter_row, textvariable=self.search_var, relief="solid", bd=1, font=("Segoe UI", 10))
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_tree())
        self.select_dupes_button = self._button(filter_row, "Select duplicates except one", self.select_duplicates_except_one, warning=True)
        self.select_dupes_button.grid(row=0, column=2, padx=(10, 4))
        self.delete_selected_button = self._button(filter_row, "Delete Selected", self.delete_selected, danger=True)
        self.delete_selected_button.grid(row=0, column=3, padx=4)

        table_frame = tk.Frame(root, bg=self.theme["surface"], highlightbackground=self.theme["border"], highlightthickness=1)
        table_frame.grid(row=3, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        default_columns = [
            "group",
            "filename",
            "size_human",
            "md5",
            "sha1",
            "crc32",
            "sha256",
            "sha384",
            "sha512",
            "extension",
            "modified_time",
            "created_time",
            "duration",
            "path",
            "error",
        ]
        self.all_columns = default_columns
        columns = [c for c in self.prefs.column_order if c in default_columns]
        for c in default_columns:
            if c not in columns:
                columns.append(c)
        self.columns = columns
        self.column_headings = {
            "group": self.t("Group"),
            "filename": self.t("Filename"),
            "size_human": self.t("Size"),
            "md5": "MD5",
            "sha1": "SHA-1",
            "crc32": "CRC32",
            "sha256": "SHA-256",
            "sha384": "SHA-384",
            "sha512": "SHA-512",
            "extension": self.t("Extension"),
            "modified_time": self.t("Modified Time"),
            "created_time": self.t("Created Time"),
            "duration": self.t("Hashing Duration"),
            "path": self.t("Full Path"),
            "error": self.t("Error"),
        }
        self.default_widths = {
            "group": 70,
            "filename": 210,
            "size_human": 100,
            "md5": 230,
            "sha1": 260,
            "crc32": 85,
            "sha256": 390,
            "sha384": 440,
            "sha512": 480,
            "extension": 90,
            "modified_time": 150,
            "created_time": 150,
            "duration": 120,
            "path": 520,
            "error": 220,
        }
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="extended")
        for col in columns:
            self.tree.heading(col, text=self.heading_text(col), command=lambda c=col: self.sort_by(c))
            anchor = "e" if col in {"size_human", "duration"} else "w"
            if col in {"group", "extension", "crc32"}:
                anchor = "center"
            min_width = self.min_column_width(col)
            width = int(self.prefs.column_widths.get(col, self.default_widths[col]))
            width = max(min_width, width)
            self.tree.column(col, width=width, minwidth=min_width, anchor=anchor, stretch=False)
        self.tree["displaycolumns"] = tuple(columns)
        self.update_sort_headings()
        ybar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview, style="Vertical.TScrollbar")
        xbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview, style="Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Delete>", lambda _e: self.delete_selected())
        self.tree.bind("<Control-a>", lambda _e: self.select_all_visible())
        self.tree.bind("<ButtonPress-1>", self.on_tree_button_press, add="+")
        self.tree.bind("<ButtonRelease-1>", self.on_tree_button_release, add="+")
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.update_stats())

        self.empty_label = tk.Label(
            table_frame,
            text=self.t("Drop one or more files/folders here. Subfolders will be scanned recursively."),
            bg=self.theme["surface"],
            fg=self.theme["muted"],
            font=("Segoe UI", 13),
            justify="center",
        )
        self.empty_label.place(relx=0.5, rely=0.5, anchor="center")

        bottom = tk.Frame(root, bg=self.theme["bg"])
        bottom.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        bottom.grid_columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value=self.last_status)
        self.stats_var = tk.StringVar(value="")
        tk.Label(bottom, textvariable=self.status_var, bg=self.theme["bg"], fg=self.theme["muted"], font=("Segoe UI", 10), anchor="w").grid(row=0, column=0, sticky="ew")
        self.progress = ttk.Progressbar(bottom, mode="determinate", maximum=100, length=260)
        self.progress.grid(row=0, column=1, sticky="e", padx=(12, 0))
        tk.Label(bottom, textvariable=self.stats_var, bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10, "bold"), anchor="e").grid(row=0, column=2, sticky="e", padx=(12, 0))

        self._create_context_menu()
        self._register_drop_target_recursive(self.root, self.add_paths)
        self.refresh_tree()
        self.update_buttons()

    def heading_text(self, col: str) -> str:
        label = self.column_headings.get(col, col)
        if self.sort_column == col:
            return f"{label} {'▼' if self.sort_reverse else '▲'}"
        return label

    def update_sort_headings(self) -> None:
        if not hasattr(self, "tree") or not hasattr(self, "column_headings"):
            return
        try:
            for col in getattr(self, "all_columns", []):
                if col in getattr(self, "column_headings", {}):
                    self.tree.heading(col, text=self.heading_text(col), command=lambda c=col: self.sort_by(c))
        except Exception as exc:
            LOG.debug("update_sort_headings failed: %r", exc)

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", background=self.theme["surface"], fieldbackground=self.theme["surface"], foreground=self.theme["text"], rowheight=24, bordercolor=self.theme["border"], borderwidth=1)
        style.configure("Treeview.Heading", background=self.theme["surface2"], foreground=self.theme["text"], font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", self.theme["accent"])], foreground=[("selected", "#ffffff")])
        style.configure("TCombobox", fieldbackground=self.theme["surface"], background=self.theme["surface2"], foreground=self.theme["text"], selectbackground=self.theme["surface"], selectforeground=self.theme["text"], arrowcolor=self.theme["text"], bordercolor=self.theme["border"], lightcolor=self.theme["border"], darkcolor=self.theme["border"])
        style.map("TCombobox", fieldbackground=[("readonly", self.theme["surface"])], foreground=[("readonly", self.theme["text"])], selectbackground=[("readonly", self.theme["surface"])], selectforeground=[("readonly", self.theme["text"])])
        style.configure("TProgressbar", troughcolor=self.theme["surface2"], background=self.theme["accent"], bordercolor=self.theme["border"])
        if self.prefs.theme == "dark":
            scrollbar_trough = "#0b1220"
            scrollbar_thumb = "#cbd5e1"
            scrollbar_active = "#f8fafc"
        else:
            scrollbar_trough = "#f1f5f9"
            scrollbar_thumb = "#64748b"
            scrollbar_active = "#334155"
        for style_name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
            style.configure(
                style_name,
                troughcolor=scrollbar_trough,
                background=scrollbar_thumb,
                bordercolor=self.theme["border"],
                arrowcolor=scrollbar_thumb,
                lightcolor=scrollbar_thumb,
                darkcolor=scrollbar_thumb,
            )
            style.map(
                style_name,
                background=[("active", scrollbar_active), ("pressed", scrollbar_active), ("!disabled", scrollbar_thumb)],
                arrowcolor=[("active", scrollbar_active), ("pressed", scrollbar_active), ("!disabled", scrollbar_thumb)],
            )

    def _button(self, parent: tk.Widget, key: str, command: Callable, *, primary: bool = False, danger: bool = False, warning: bool = False) -> tk.Button:
        bg = self.theme["surface2"]
        fg = self.theme["text"]
        if primary:
            bg = self.theme["accent"]
            fg = "#ffffff"
        elif danger:
            bg = self.theme["danger"]
            fg = "#ffffff"
        elif warning:
            bg = self.theme["warning"]
            fg = "#ffffff"
        return tk.Button(
            parent,
            text=self.t(key),
            command=command,
            bg=bg,
            fg=fg,
            activebackground=self.theme.get("accent_hover", bg),
            activeforeground="#ffffff" if (primary or danger or warning) else self.theme["text"],
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            font=("Segoe UI", 10, "bold" if primary else "normal"),
        )

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=self.t("Add Files"), command=self.add_files)
        file_menu.add_command(label=self.t("Add Folder"), command=self.add_folder)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("Export CSV"), command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("Clear List"), command=self.clear_all)
        file_menu.add_separator()
        file_menu.add_command(label=self.t("Exit"), command=self.on_close)
        menubar.add_cascade(label=self.t("File"), menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label=self.t("Select All Visible"), command=self.select_all_visible)
        edit_menu.add_command(label=self.t("Select duplicates except one"), command=self.select_duplicates_except_one)
        edit_menu.add_separator()
        for alg in ["md5", "sha1", "crc32", "sha256", "sha384", "sha512"]:
            edit_menu.add_command(label=f"{self.t('Copy')} {DISPLAY_NAMES[alg]}", command=lambda a=alg: self.copy_selected_hash(a))
        edit_menu.add_separator()
        edit_menu.add_command(label=self.t("Copy Selected Paths"), command=self.copy_selected_paths)
        edit_menu.add_command(label=self.t("Copy Selected Rows"), command=self.copy_selected_rows)
        edit_menu.add_separator()
        edit_menu.add_command(label=self.t("Open File Location"), command=self.open_selected_file_location)
        edit_menu.add_command(label=self.t("Remove Selected from List"), command=self.remove_selected_from_list)
        edit_menu.add_command(label=self.t("Delete Selected"), command=self.delete_selected)
        menubar.add_cascade(label=self.t("Edit"), menu=edit_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label=self.t("Settings"), command=self.open_settings)
        tools_menu.add_command(label=self.t("Restore Defaults"), command=self.restore_defaults)
        tools_menu.add_command(label=self.t("Open Log Folder"), command=lambda: self.open_folder(log_dir()))
        tools_menu.add_command(label=self.t("Report Bug / Request Feature"), command=self.report_bug)
        menubar.add_cascade(label=self.t("Tools"), menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=self.t("GitHub Repository"), command=lambda: webbrowser.open(GITHUB_URL))
        help_menu.add_command(label=self.t("Check for Updates"), command=lambda: self.check_for_updates_silent(manual=True))
        help_menu.add_command(label=self.t("Report Bug / Request Feature"), command=self.report_bug)
        help_menu.add_command(label=self.t("Email Author"), command=lambda: webbrowser.open("mailto:{email}?subject={subject}".format(email=AUTHOR_EMAIL, subject=urllib.parse.quote(self.t("HashSieve feedback")))))
        help_menu.add_separator()
        help_menu.add_command(label=self.t("GitHub Sponsors"), command=lambda: webbrowser.open(SPONSOR_URL))
        help_menu.add_command(label=self.t("Buy Me a Coffee"), command=lambda: webbrowser.open(BUYMEACOFFEE_URL))
        help_menu.add_separator()
        help_menu.add_command(label=self.t("About"), command=self.show_about)
        menubar.add_cascade(label=self.t("Help"), menu=help_menu)
        self.root.config(menu=menubar)

    def _create_context_menu(self) -> None:
        menu = tk.Menu(self.root, tearoff=0)
        for alg in ["md5", "sha1", "crc32", "sha256", "sha384", "sha512"]:
            menu.add_command(label=f"{self.t('Copy')} {DISPLAY_NAMES[alg]}", command=lambda a=alg: self.copy_selected_hash(a))
        menu.add_separator()
        menu.add_command(label=self.t("Copy Selected Paths"), command=self.copy_selected_paths)
        menu.add_command(label=self.t("Copy Selected Rows"), command=self.copy_selected_rows)
        menu.add_separator()
        menu.add_command(label=self.t("Delete Selected"), command=self.delete_selected)
        menu.add_separator()
        menu.add_command(label=self.t("Open File Location"), command=self.open_selected_file_location)
        menu.add_command(label=self.t("Remove Selected from List"), command=self.remove_selected_from_list)
        self.context_menu = menu


    def version_tuple(self, version: str) -> tuple[int, ...]:
        parts = []
        for token in str(version).lstrip("vV").replace("-", ".").split("."):
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                parts.append(int(digits))
        return tuple(parts) or (0,)

    def check_for_updates_silent(self, manual: bool = False) -> None:
        if self.update_checked and not manual:
            return
        self.update_checked = True

        def worker() -> None:
            try:
                with urllib.request.urlopen(UPDATE_VERSION_URL, timeout=4) as resp:
                    raw = resp.read(65536).decode("utf-8", errors="replace")
                data = json.loads(raw)
                remote_version = str(data.get("version", "")).strip()
                if not remote_version:
                    if manual:
                        self.result_queue.put(("update_current", True))
                    return
                if self.version_tuple(remote_version) > self.version_tuple(APP_VERSION):
                    self.result_queue.put(("update_available", remote_version, str(data.get("release_url") or GITHUB_URL)))
                elif manual:
                    self.result_queue.put(("update_current", True))
            except Exception as exc:
                LOG.info("Update check skipped/failed: %r", exc)
                if manual:
                    self.result_queue.put(("update_current", True))

        threading.Thread(target=worker, daemon=True).start()

    def _register_drop_target(self, widget: tk.Widget, callback: Callable[[list[Path]], None]) -> bool:
        if DND_FILES is None:
            return False
        try:
            if hasattr(widget, "drop_target_register") and hasattr(widget, "dnd_bind"):
                widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                widget.dnd_bind("<<Drop>>", lambda e: callback(self._split_dnd_files(e.data)), add="+")  # type: ignore[attr-defined]
                return True
        except Exception as exc:
            LOG.debug("High-level DnD failed: %r", exc)
        try:
            widget.tk.call("package", "require", "tkdnd")
            widget.tk.call("tkdnd::drop_target", "register", widget._w, DND_FILES)  # type: ignore[attr-defined]
            command = widget.register(lambda data: callback(self._split_dnd_files(data)))
            existing = widget.tk.call("bind", widget._w, "<<Drop>>")  # type: ignore[attr-defined]
            script = f"{command} %D"
            widget.tk.call("bind", widget._w, "<<Drop>>", f"{existing}\n{script}" if existing else script)  # type: ignore[attr-defined]
            return True
        except Exception as exc:
            LOG.debug("Tcl DnD failed: %r", exc)
            return False

    def _register_drop_target_recursive(self, widget: tk.Widget, callback: Callable[[list[Path]], None]) -> bool:
        ok = self._register_drop_target(widget, callback)
        try:
            for child in widget.winfo_children():
                ok = self._register_drop_target_recursive(child, callback) or ok
        except Exception:
            pass
        return ok

    def _split_dnd_files(self, data: str) -> list[Path]:
        try:
            items = self.root.tk.splitlist(data)
        except Exception:
            items = [data]
        return [Path(x) for x in items]

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(parent=self.root, title=self.t("Select files"))
        if paths:
            self.add_paths([Path(p) for p in paths])

    def add_folder(self) -> None:
        path = filedialog.askdirectory(parent=self.root, title=self.t("Select folder"))
        if path:
            self.add_paths([Path(path)])

    def is_busy(self) -> bool:
        return bool(self.running or self.scan_running)

    def add_paths(self, paths: Iterable[Path]) -> None:
        paths = [Path(p) for p in paths]
        if not paths:
            return
        if self.is_busy():
            self.set_status(self.t("Busy now. Please wait until scanning/hashing finishes before adding more files or folders."))
            return
        self.stop_event.clear()
        self.scan_running = True
        self.scan_count = 0
        self.scan_bytes = 0
        self.done_count = 0
        self.total_to_hash = 0
        self.bytes_done = 0
        self.total_bytes_to_hash = 0
        self.hash_pending_after_run = False
        self.progress.configure(mode="indeterminate", value=0, maximum=100) if hasattr(self, "progress") else None
        try:
            self.progress.start(12)
        except Exception:
            pass
        self.update_buttons()
        if hasattr(self, "empty_label") and not self.entries:
            self.empty_label.configure(text=self.t("Scanning files recursively..."))
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.set_status(self.t("Scanning files recursively..."))
        self.scan_thread = threading.Thread(target=self._scan_thread_main, args=(paths,), daemon=True)
        self.scan_thread.start()

    def _scan_thread_main(self, paths: list[Path]) -> None:
        try:
            def progress_callback(count: int, total_bytes: int, last_path: str) -> None:
                self.result_queue.put(("scan_progress", int(count), int(total_bytes), last_path))
            scanned = scan_paths(
                paths,
                follow_symlinks=bool(self.prefs.follow_symlinks),
                include_hidden=bool(self.prefs.include_hidden),
                stop_event=self.stop_event,
                progress_callback=progress_callback,
            )
            self.result_queue.put(("scan_done", scanned, bool(self.stop_event.is_set())))
        except Exception as exc:
            self.result_queue.put(("fatal", str(exc), traceback.format_exc()))
            self.result_queue.put(("scan_done", [], True))

    def _add_scanned_files_to_entries(self, scanned: list[ScannedFile]) -> int:
        added = 0
        for item in scanned:
            key = item.key
            if key in self.entries:
                continue
            e = FileEntry(path=item.path, key=key, name=item.name, extension=item.extension)
            e.size = item.size
            e.modified_time = item.modified_time
            e.created_time = item.created_time
            e.error = item.error
            self.entries[key] = e
            self.order.append(key)
            added += 1
        return added

    def clear_all(self) -> None:
        if self.is_busy():
            messagebox.showwarning(self.t("Hashing is running"), self.t("Please stop or wait for scanning/hashing to finish first."), parent=self.root)
            return
        if self.entries and not messagebox.askyesno(self.t("Clear list"), self.t("Remove all rows from the list? This does not delete files from disk."), parent=self.root):
            return
        self.entries.clear()
        self.order.clear()
        self.done_count = 0
        self.total_to_hash = 0
        self.bytes_done = 0
        self.total_bytes_to_hash = 0
        self.progress.configure(mode="determinate", value=0, maximum=100) if hasattr(self, "progress") else None
        self.refresh_tree()
        self.set_status(self.t("List cleared."))

    def start_hashing(self, *, only_missing: bool = False) -> None:
        if self.running:
            return
        if not self.entries:
            self.refresh_tree()
            self.set_status(self.t("No files need hashing."))
            return
        try:
            self.prefs.workers = max(1, min(64, int(self.workers_var.get())))
        except Exception:
            self.prefs.workers = default_worker_count()
        self.prefs.save()
        if only_missing:
            keys = [k for k in self.order if not self.entries[k].hashes and not self.entries[k].error]
        else:
            keys = list(self.order)
        jobs = [(k, str(self.entries[k].path)) for k in keys if k in self.entries]
        if not jobs:
            self.recompute_groups()
            self.refresh_tree(keep_selection=True)
            self.set_status(self.t("No files need hashing."))
            self.update_buttons()
            return
        self.running = True
        self.done_count = 0
        self.total_to_hash = len(jobs)
        self.bytes_done = 0
        self.total_bytes_to_hash = sum(max(0, self.entries[k].size) for k, _path in jobs if k in self.entries)
        self.stop_event.clear()
        try:
            self.progress.stop()
        except Exception:
            pass
        self.progress.configure(mode="determinate", value=0, maximum=max(1, self.total_bytes_to_hash))
        self.last_progress_ui_update = 0.0
        self.hash_start_monotonic = monotonic()
        self.hash_last_rate_time = self.hash_start_monotonic
        self.hash_last_rate_done = 0
        self.hash_last_rate_bytes = 0
        self.update_buttons()
        if hasattr(self, "empty_label") and not self.tree.get_children():
            self.empty_label.configure(text=self.t("Hashing files... The result table will be built after hashing finishes."))
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        self.set_status(self.t("Hashing {count} file(s)...").format(count=self.total_to_hash))
        self.hash_thread = threading.Thread(target=self._hash_thread_main, args=(jobs, self.prefs.workers), daemon=True)
        self.hash_thread.start()

    def _hash_thread_main(self, jobs: list[tuple[str, str]], workers: int) -> None:
        try:
            work_queue: queue.Queue[tuple[str, str]] = queue.Queue()
            for job in jobs:
                work_queue.put(job)

            def worker_loop() -> None:
                while not self.stop_event.is_set():
                    try:
                        key, path = work_queue.get_nowait()
                    except queue.Empty:
                        return
                    try:
                        def progress_callback(delta: int, _key=key) -> None:
                            self.result_queue.put(("hash_progress", _key, int(delta)))
                        result = compute_file_hashes(path, progress_callback=progress_callback)
                    except Exception as exc:
                        result = FileHashResult(path=path, error=repr(exc))
                    self.result_queue.put(("hash_result", key, result))
                    work_queue.task_done()

            n_workers = max(1, min(int(workers), len(jobs)))
            with ThreadPoolExecutor(max_workers=n_workers) as executor:
                futures = [executor.submit(worker_loop) for _ in range(n_workers)]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        self.result_queue.put(("fatal", str(exc), traceback.format_exc()))
        except Exception as exc:
            self.result_queue.put(("fatal", str(exc), traceback.format_exc()))
        finally:
            self.result_queue.put(("hash_done",))

    def stop_hashing(self) -> None:
        if self.scan_running:
            self.stop_event.set()
            self.set_status(self.t("Stopping scan..."))
        elif self.running:
            self.stop_event.set()
            self.set_status(self.t("Stopping after current file(s)..."))

    def hash_progress_text(self, *, include_percent: bool = True) -> str:
        elapsed = max(0.001, monotonic() - getattr(self, "hash_start_monotonic", monotonic()))
        files_per_sec = float(getattr(self, "done_count", 0)) / elapsed
        bytes_per_sec = float(getattr(self, "bytes_done", 0)) / elapsed
        total_bytes = max(1, getattr(self, "total_bytes_to_hash", 1))
        percent = getattr(self, "bytes_done", 0) * 100.0 / total_bytes
        template = self.t("Hashing progress: {done}/{total} file(s), {bytes_done}/{bytes_total} ({percent:.1f}%). Speed: {files_per_sec:.2f} files/s, {bytes_per_sec}/s.")
        if not include_percent:
            template = self.t("Hashing progress: {done}/{total} file(s), {bytes_done}/{bytes_total}. Speed: {files_per_sec:.2f} files/s, {bytes_per_sec}/s.")
        return template.format(
            done=getattr(self, "done_count", 0),
            total=getattr(self, "total_to_hash", 0),
            bytes_done=bytes_to_human(getattr(self, "bytes_done", 0)),
            bytes_total=bytes_to_human(getattr(self, "total_bytes_to_hash", 0)),
            percent=percent,
            files_per_sec=files_per_sec,
            bytes_per_sec=bytes_to_human(bytes_per_sec),
        )

    def poll_queue(self) -> None:
        processed = 0
        try:
            while processed < 1000:
                processed += 1
                item = self.result_queue.get_nowait()
                kind = item[0]
                if kind == "scan_progress":
                    _kind, count, total_bytes, last_path = item
                    self.scan_count = int(count)
                    self.scan_bytes = int(total_bytes)
                    now = monotonic()
                    if now - self.last_progress_ui_update >= 0.20:
                        self.last_progress_ui_update = now
                        self.set_status(self.t("Scanning files: {count} found, {size} total...").format(count=self.scan_count, size=bytes_to_human(self.scan_bytes)))
                elif kind == "scan_done":
                    _kind, scanned, was_stopped = item
                    self.scan_running = False
                    try:
                        self.progress.stop()
                        self.progress.configure(mode="determinate", value=0 if was_stopped else 100, maximum=100)
                    except Exception:
                        pass
                    added = self._add_scanned_files_to_entries(scanned)
                    if was_stopped:
                        self.update_buttons()
                        self.refresh_tree(keep_selection=True)
                        self.set_status(self.t("Scanning stopped. Added {count} new file(s).").format(count=added))
                    elif added:
                        self.set_status(self.t("Scanning complete. Added {count} new file(s). Starting hash calculation...").format(count=added))
                        self.update_stats()
                        self.root.after(50, lambda: self.start_hashing(only_missing=True))
                    else:
                        self.update_buttons()
                        self.refresh_tree(keep_selection=True)
                        self.set_status(self.t("No new files were added. The selected paths may already be in the list."))
                elif kind == "hash_result":
                    _kind, key, result = item
                    entry = self.entries.get(key)
                    if entry:
                        entry.update_from_result(result)
                    self.done_count += 1
                    now = monotonic()
                    if now - self.last_progress_ui_update >= 0.30 or self.done_count == self.total_to_hash:
                        self.last_progress_ui_update = now
                        self.set_status(self.hash_progress_text(include_percent=False))
                elif kind == "hash_progress":
                    _kind, _key, delta = item
                    self.bytes_done = min(getattr(self, "total_bytes_to_hash", 0), getattr(self, "bytes_done", 0) + max(0, int(delta)))
                    self.progress.configure(value=self.bytes_done)
                    now = monotonic()
                    if now - self.last_progress_ui_update >= 0.30:
                        self.last_progress_ui_update = now
                        total_bytes = max(1, getattr(self, "total_bytes_to_hash", 1))
                        percent = self.bytes_done * 100.0 / total_bytes
                        self.set_status(self.hash_progress_text(include_percent=True))
                elif kind == "fatal":
                    messagebox.showerror(self.t("Hashing error"), f"{item[1]}\n\n{item[2]}", parent=self.root)
                elif kind == "update_available":
                    _kind, remote_version, release_url = item
                    if messagebox.askyesno(
                        self.t("Update Available"),
                        self.t("A newer version of HashSieve is available: {version}. Open the GitHub repository now?").format(version=remote_version),
                        parent=self.root,
                    ):
                        webbrowser.open(release_url or GITHUB_URL)
                elif kind == "update_current":
                    manual = bool(item[1]) if len(item) > 1 else False
                    self.set_status(self.t("You are using the latest version."))
                    if manual:
                        messagebox.showinfo(self.t("No Updates"), self.t("You are using the latest version."), parent=self.root)
                elif kind == "hash_done":
                    was_stopped = self.stop_event.is_set()
                    self.running = False
                    try:
                        self.progress.stop()
                    except Exception:
                        pass
                    if was_stopped:
                        self.progress.configure(mode="determinate", value=0, maximum=max(1, getattr(self, "total_bytes_to_hash", 1)))
                    else:
                        self.progress.configure(mode="determinate", value=max(1, getattr(self, "total_bytes_to_hash", 0)), maximum=max(1, getattr(self, "total_bytes_to_hash", 1)))
                    self.set_status(self.t("Hashing finished. Building result table..."))
                    self.root.update_idletasks()
                    self.recompute_groups()
                    self.refresh_tree(keep_selection=False)
                    self.update_buttons()
                    if was_stopped:
                        self.set_status(self.t("Hashing stopped. Completed {done}/{total} file(s).").format(done=self.done_count, total=self.total_to_hash))
                    else:
                        self.set_status(self.t("Hashing complete. Found {groups} duplicate group(s), {dupes} duplicate file(s).").format(groups=self.count_duplicate_groups(), dupes=self.count_duplicate_files()))
        except queue.Empty:
            pass
        self.root.after(100, self.poll_queue)

    def duplicate_identity(self, entry: FileEntry) -> tuple | None:
        if entry.error:
            return None
        if bool(getattr(self.prefs, "ignore_empty_files_for_groups", True)) and int(entry.size) == 0:
            return None
        if any(not entry.hashes.get(alg) for alg in HASH_COLUMNS):
            return None
        return (entry.size, *(entry.hashes.get(alg, "") for alg in HASH_COLUMNS))

    def recompute_groups(self) -> None:
        buckets: dict[tuple, list[str]] = {}
        for key, entry in self.entries.items():
            entry.duplicate_group = 0
            identity = self.duplicate_identity(entry)
            if identity is None:
                continue
            buckets.setdefault(identity, []).append(key)
        group_id = 1
        for _bucket, keys in sorted(buckets.items(), key=lambda kv: (len(kv[1]), kv[0][0]), reverse=True):
            if len(keys) < 2:
                continue
            for key in keys:
                self.entries[key].duplicate_group = group_id
            group_id += 1

    def refresh_tree(self, keep_selection: bool = False) -> None:
        if not hasattr(self, "tree"):
            return
        selected = set(self.tree.selection()) if keep_selection else set()
        children = self.tree.get_children()
        for i in range(0, len(children), 1000):
            self.tree.delete(*children[i:i + 1000])
            if i and i % 5000 == 0:
                self.root.update_idletasks()
        colors = GROUP_COLORS_DARK if self.prefs.theme == "dark" else GROUP_COLORS_LIGHT
        self.tree.tag_configure("error", foreground=self.theme["danger"])
        for i, color in enumerate(colors, start=1):
            self.tree.tag_configure(f"group_color_{i}", background=color)

        keys = list(self.order)
        if self.sort_column:
            if self.sort_column == "group":
                if self.sort_reverse:
                    keys.sort(key=lambda k: (0, -self.entries[k].duplicate_group) if self.entries[k].duplicate_group > 0 else (1, 0))
                else:
                    keys.sort(key=lambda k: (0, self.entries[k].duplicate_group) if self.entries[k].duplicate_group > 0 else (1, 0))
            else:
                keys.sort(key=lambda k: self._sort_value(self.entries[k], self.sort_column or ""), reverse=self.sort_reverse)

        query = ""
        if hasattr(self, "search_var"):
            query = self.search_var.get().strip().lower()
        dup_only = bool(getattr(self, "duplicates_only_var", tk.BooleanVar(value=False)).get()) if hasattr(self, "duplicates_only_var") else False
        visible: list[str] = []
        for key in keys:
            entry = self.entries.get(key)
            if entry is None:
                continue
            if dup_only and entry.duplicate_group <= 0:
                continue
            if query and query not in self._search_blob(entry):
                continue
            tags: list[str] = []
            if entry.duplicate_group > 0:
                tags.append(f"group_color_{((entry.duplicate_group - 1) % len(colors)) + 1}")
            if entry.error:
                tags.append("error")
            values = self._entry_values(entry)
            self.tree.insert("", "end", iid=key, values=values, tags=tuple(tags))
            visible.append(key)
            if len(visible) % 2000 == 0:
                self.set_status(self.t("Building result table... {count} rows").format(count=len(visible)))
                self.root.update_idletasks()
        self.displayed_keys = visible
        try:
            for key in selected:
                if key in visible:
                    self.tree.selection_add(key)
        except Exception:
            pass
        if len(self.entries) == 0:
            self.empty_label.configure(text=self.t("Drop one or more files/folders here. Subfolders will be scanned recursively."))
            self.empty_label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.empty_label.place_forget()
        self.update_stats()
        try:
            building_prefix = self.t("Building result table...").split("{")[0].strip()
            if str(self.last_status).startswith(building_prefix):
                self.set_status(self.t("Result table updated. {count} row(s) visible.").format(count=len(visible)))
        except Exception:
            pass

    def _entry_values(self, entry: FileEntry) -> tuple:
        group = str(entry.duplicate_group) if entry.duplicate_group > 0 else ""
        values = {
            "group": group,
            "filename": entry.name,
            "size_human": bytes_to_human(entry.size),
            "md5": entry.hashes.get("md5", ""),
            "sha1": entry.hashes.get("sha1", ""),
            "crc32": entry.hashes.get("crc32", ""),
            "sha256": entry.hashes.get("sha256", ""),
            "sha384": entry.hashes.get("sha384", ""),
            "sha512": entry.hashes.get("sha512", ""),
            "extension": entry.extension,
            "modified_time": entry.modified_time,
            "created_time": entry.created_time,
            "duration": f"{entry.duration_seconds:.3f}s" if entry.duration_seconds else "",
            "path": str(entry.path),
            "error": entry.error,
        }
        return tuple(values.get(col, "") for col in getattr(self, "columns", []))

    def _sort_value(self, entry: FileEntry, col: str):
        if col == "group":
            return entry.duplicate_group
        if col == "filename":
            return entry.name.lower()
        if col == "size_human":
            return entry.size
        if col in HASH_COLUMNS:
            return entry.hashes.get(col, "")
        if col == "duration":
            return entry.duration_seconds
        return str(getattr(entry, col, "")).lower()

    def sort_by(self, col: str) -> None:
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        self.prefs.sort_column = self.sort_column or ""
        self.prefs.sort_reverse = bool(self.sort_reverse)
        self.prefs.save()
        self.update_sort_headings()
        self.refresh_tree(keep_selection=True)

    def _search_blob(self, entry: FileEntry) -> str:
        values = [entry.name, entry.extension, str(entry.path), entry.error, str(entry.duplicate_group)]
        values.extend(entry.hashes.values())
        return "\n".join(values).lower()

    def update_stats(self) -> None:
        total = len(self.entries)
        total_size = sum(e.size for e in self.entries.values())
        groups = self.count_duplicate_groups()
        dupes = self.count_duplicate_files()
        selected = len(self.tree.selection()) if hasattr(self, "tree") else 0
        if hasattr(self, "stats_var"):
            self.stats_var.set(self.t("Files: {files} | Size: {size} | Duplicate groups: {groups} | Duplicate files: {dupes} | Selected: {selected}").format(
                files=total,
                size=bytes_to_human(total_size),
                groups=groups,
                dupes=dupes,
                selected=selected,
            ))

    def update_buttons(self) -> None:
        busy = self.is_busy()
        normal_if_idle = tk.DISABLED if busy else tk.NORMAL
        stop_state = tk.NORMAL if busy else tk.DISABLED
        for name in ["add_files_button", "add_folder_button", "clear_button", "export_button", "select_dupes_button", "delete_selected_button"]:
            if hasattr(self, name):
                getattr(self, name).configure(state=normal_if_idle)
        if hasattr(self, "stop_button"):
            self.stop_button.configure(state=stop_state)

    def set_status(self, text: str) -> None:
        self.last_status = text
        if hasattr(self, "status_var"):
            self.status_var.set(text)

    def count_duplicate_groups(self) -> int:
        return len({e.duplicate_group for e in self.entries.values() if e.duplicate_group > 0})

    def count_duplicate_files(self) -> int:
        counts: dict[int, int] = {}
        for e in self.entries.values():
            if e.duplicate_group > 0:
                counts[e.duplicate_group] = counts.get(e.duplicate_group, 0) + 1
        return sum(max(0, n - 1) for n in counts.values())

    def on_workers_changed(self) -> None:
        try:
            self.prefs.workers = max(1, min(64, int(self.workers_var.get())))
            self.prefs.save()
        except Exception:
            pass

    def on_recycle_changed(self) -> None:
        self.prefs.recycle_bin = bool(self.recycle_var.get())
        self.prefs.save()

    def select_all_visible(self) -> str:
        self.tree.selection_set(self.displayed_keys)
        return "break"

    def selected_entries(self) -> list[FileEntry]:
        out: list[FileEntry] = []
        for key in self.tree.selection():
            e = self.entries.get(str(key))
            if e is not None:
                out.append(e)
        return out

    def show_context_menu(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if row and row not in self.tree.selection():
            self.tree.selection_set(row)
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_to_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.set_status(self.t("Copied to clipboard."))

    def copy_selected_hash(self, alg: str) -> None:
        values = [e.hashes.get(alg, "") for e in self.selected_entries() if e.hashes.get(alg)]
        if not values:
            self.set_status(self.t("No selected hash values to copy."))
            return
        self.copy_to_clipboard("\n".join(values))

    def copy_selected_paths(self) -> None:
        paths = [str(e.path) for e in self.selected_entries()]
        if paths:
            self.copy_to_clipboard("\n".join(paths))

    def copy_selected_rows(self) -> None:
        rows = []
        header = ["group", "filename", "size_bytes", "md5", "sha1", "crc32", "sha256", "sha384", "sha512", "path", "error"]
        rows.append("\t".join(header))
        for e in self.selected_entries():
            rows.append("\t".join([
                str(e.duplicate_group),
                e.name,
                str(e.size),
                e.hashes.get("md5", ""),
                e.hashes.get("sha1", ""),
                e.hashes.get("crc32", ""),
                e.hashes.get("sha256", ""),
                e.hashes.get("sha384", ""),
                e.hashes.get("sha512", ""),
                str(e.path),
                e.error,
            ]))
        if len(rows) > 1:
            self.copy_to_clipboard("\n".join(rows))

    def select_duplicates_except_one(self) -> None:
        groups: dict[int, list[FileEntry]] = {}
        for e in self.entries.values():
            if e.duplicate_group > 0:
                groups.setdefault(e.duplicate_group, []).append(e)
        if not groups:
            messagebox.showinfo(self.t("No duplicates"), self.t("No duplicate groups are available. Calculate hashes first."), parent=self.root)
            return
        keys_to_select: list[str] = []
        for group_entries in groups.values():
            group_entries.sort(key=lambda e: (len(str(e.path)), str(e.path).lower()))
            # Keep the shortest path / alphabetically earliest path in each group.
            for e in group_entries[1:]:
                if e.key in self.displayed_keys:
                    keys_to_select.append(e.key)
        self.refresh_tree(keep_selection=False)
        self.tree.selection_set(keys_to_select)
        self.update_stats()
        self.set_status(self.t("Selected {count} duplicate copy/copies while keeping one file in each group. You can Ctrl-click to adjust the selection before deleting.").format(count=len(keys_to_select)))

    def delete_selected(self) -> None:
        self._delete_entries(self.selected_entries(), selected_only=True)

    def _delete_entries(self, entries: list[FileEntry], *, selected_only: bool) -> None:
        if not entries:
            messagebox.showinfo(self.t("Nothing to delete"), self.t("No files are selected for deletion."), parent=self.root)
            return
        total_size = sum(e.size for e in entries)
        use_recycle = bool(self.prefs.recycle_bin)
        if use_recycle and send2trash is None:
            messagebox.showwarning(
                self.t("Recycle bin unavailable"),
                self.t("send2trash is not installed, so recycle-bin deletion is unavailable. The operation will be cancelled."),
                parent=self.root,
            )
            return
        msg = self.t("Delete {count} file(s), total {size}?\n\nMode: {mode}\n\nThis action changes files on disk.").format(
            count=len(entries),
            size=bytes_to_human(total_size),
            mode=self.t("Move to Recycle Bin") if use_recycle else self.t("Permanent delete"),
        )
        if not messagebox.askyesno(self.t("Confirm deletion"), msg, parent=self.root):
            return
        if not use_recycle:
            confirm = self.t("Type DELETE to permanently delete the selected files:")
            typed = self.simple_prompt(self.t("Permanent delete confirmation"), confirm)
            if typed != "DELETE":
                self.set_status(self.t("Permanent deletion cancelled."))
                return
        failed: list[str] = []
        deleted_keys: list[str] = []
        for e in entries:
            try:
                if use_recycle:
                    send2trash(str(e.path))  # type: ignore[misc]
                else:
                    os.remove(e.path)
                deleted_keys.append(e.key)
            except Exception as exc:
                failed.append(f"{e.path}: {exc}")
        for key in deleted_keys:
            self.entries.pop(key, None)
        self.order = [k for k in self.order if k in self.entries]
        self.recompute_groups()
        self.refresh_tree()
        if failed:
            messagebox.showwarning(self.t("Some files could not be deleted"), "\n".join(failed[:20]), parent=self.root)
        self.set_status(self.t("Deleted {deleted} file(s). Failed: {failed}.").format(deleted=len(deleted_keys), failed=len(failed)))

    def simple_prompt(self, title: str, prompt: str) -> str | None:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        win.grab_set()
        win.configure(bg=self.theme["bg"])
        win.geometry("460x160")
        result = {"value": None}
        tk.Label(win, text=prompt, bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10), wraplength=420, justify="left").pack(fill=tk.X, padx=18, pady=(18, 8))
        var = tk.StringVar()
        entry = tk.Entry(win, textvariable=var, font=("Segoe UI", 11))
        entry.pack(fill=tk.X, padx=18, pady=8)
        entry.focus_set()
        row = tk.Frame(win, bg=self.theme["bg"])
        row.pack(fill=tk.X, padx=18, pady=8)
        def ok():
            result["value"] = var.get()
            win.destroy()
        def cancel():
            win.destroy()
        self._button(row, "OK", ok, primary=True).pack(side=tk.RIGHT, padx=(6, 0))
        self._button(row, "Cancel", cancel).pack(side=tk.RIGHT)
        win.bind("<Return>", lambda _e: ok())
        self.root.wait_window(win)
        return result["value"]

    def remove_selected_from_list(self) -> None:
        keys = [str(k) for k in self.tree.selection()]
        for key in keys:
            self.entries.pop(key, None)
        self.order = [k for k in self.order if k in self.entries]
        self.recompute_groups()
        self.refresh_tree()

    def on_tree_double_click(self, event) -> str | None:
        try:
            region = self.tree.identify_region(event.x, event.y)
            if region == "separator":
                col = self.column_from_tree_id(self.tree.identify_column(event.x))
                if col:
                    self.auto_fit_column(col)
                    return "break"
            if region == "heading":
                return "break"
        except Exception:
            pass
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            entry = self.entries.get(str(row))
            if entry:
                self.open_file_location(entry.path)
                return "break"
        return None

    def open_selected_file_location(self) -> None:
        selected = self.selected_entries()
        if selected:
            self.open_file_location(selected[0].path)

    def open_selected_folder(self) -> None:
        self.open_selected_file_location()

    def open_file_location(self, file_path: Path) -> None:
        file_path = Path(file_path)
        try:
            if os.name == "nt":
                target = str(file_path)
                if file_path.exists():
                    # explorer.exe expects /select,"C:\path\file" as one argument.
                    subprocess.Popen(["explorer.exe", f'/select,"{target}"'])
                else:
                    subprocess.Popen(["explorer.exe", str(file_path.parent)])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(file_path)])
            else:
                self.open_folder(file_path.parent)
        except Exception as exc:
            messagebox.showerror(self.t("Open folder failed"), str(exc), parent=self.root)

    def open_folder(self, path: Path) -> None:
        path = Path(path)
        try:
            path.mkdir(parents=True, exist_ok=True) if not path.exists() and path.suffix == "" else None
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as exc:
            messagebox.showerror(self.t("Open folder failed"), str(exc), parent=self.root)

    def export_csv(self) -> None:
        if not self.entries:
            messagebox.showwarning(self.t("No data"), self.t("There is no data to export."), parent=self.root)
            return
        initialdir = self.prefs.last_export_dir or str(Path.home() / "Desktop")
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title=self.t("Export CSV"),
            defaultextension=".csv",
            initialdir=initialdir,
            initialfile=f"HashSieve_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            filetypes=[("CSV", "*.csv"), (self.t("All files"), "*.*")],
        )
        if not filename:
            return
        path = Path(filename)
        self.prefs.last_export_dir = str(path.parent)
        self.prefs.save()
        header = [
            "duplicate_group",
            "filename",
            "extension",
            "file_size_bytes",
            "file_size_human",
            "md5",
            "sha1",
            "crc32",
            "sha256",
            "sha384",
            "sha512",
            "full_path",
            "modified_time",
            "created_time",
            "hash_start_time",
            "hash_end_time",
            "hashing_duration_seconds",
            "error",
        ]
        try:
            with path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(header)
                for key in self.order:
                    e = self.entries[key]
                    writer.writerow([
                        e.duplicate_group or "",
                        e.name,
                        e.extension,
                        e.size,
                        bytes_to_human(e.size),
                        e.hashes.get("md5", ""),
                        e.hashes.get("sha1", ""),
                        e.hashes.get("crc32", ""),
                        e.hashes.get("sha256", ""),
                        e.hashes.get("sha384", ""),
                        e.hashes.get("sha512", ""),
                        str(e.path),
                        e.modified_time,
                        e.created_time,
                        e.hash_start_time,
                        e.hash_end_time,
                        f"{e.duration_seconds:.6f}" if e.duration_seconds else "",
                        e.error,
                    ])
            self.set_status(self.t("CSV exported: {path}").format(path=str(path)))
        except Exception as exc:
            messagebox.showerror(self.t("Export failed"), str(exc), parent=self.root)

    def restore_defaults(self) -> None:
        if self.is_busy():
            messagebox.showwarning(self.t("Hashing is running"), self.t("Please stop or wait for scanning/hashing to finish first."), parent=self.root)
            return
        if not messagebox.askyesno(self.t("Restore Defaults"), self.t("Restore all settings to their default values?"), parent=self.root):
            return
        geometry = self.root.geometry()
        self.prefs = Preferences.defaults()
        self.prefs.window_geometry = geometry
        self.prefs.save()
        self.translator.load(self.prefs.language)
        self.build_ui()
        self.set_status(self.t("Default settings restored."))

    def open_settings(self) -> None:
        if self.is_busy():
            messagebox.showwarning(self.t("Hashing is running"), self.t("Please stop or wait for scanning/hashing to finish first."), parent=self.root)
            return
        win = tk.Toplevel(self.root)
        win.title(self.t("Settings"))
        win.configure(bg=self.theme["bg"])
        win.geometry("600x470")
        win.transient(self.root)
        win.grab_set()
        frame = tk.Frame(win, bg=self.theme["bg"])
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        tk.Label(frame, text=self.t("Language"), bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=8)
        language_names = list(SUPPORTED_LANGUAGES.values())
        name_to_code = {name: code for code, name in SUPPORTED_LANGUAGES.items()}
        code_to_name = dict(SUPPORTED_LANGUAGES)
        lang_var = tk.StringVar(value=code_to_name.get(self.prefs.language, code_to_name.get("en-US", "English")))
        lang_combo = ttk.Combobox(frame, textvariable=lang_var, state="readonly", values=language_names)
        lang_combo.grid(row=0, column=1, sticky="ew", pady=8)
        lang_combo.bind("<<ComboboxSelected>>", lambda _e: self.root.after(30, lambda: self.clear_combobox_focus(lang_combo, win)))

        tk.Label(frame, text=self.t("Theme"), bg=self.theme["bg"], fg=self.theme["text"], font=("Segoe UI", 10, "bold")).grid(row=1, column=0, sticky="w", pady=8)
        theme_options = {self.t("Light"): "light", self.t("Dark"): "dark"}
        current_theme_label = next((label for label, value in theme_options.items() if value == self.prefs.theme), self.t("Light"))
        theme_var = tk.StringVar(value=current_theme_label)
        theme_combo = ttk.Combobox(frame, textvariable=theme_var, state="readonly", values=list(theme_options.keys()))
        theme_combo.grid(row=1, column=1, sticky="ew", pady=8)
        theme_combo.bind("<<ComboboxSelected>>", lambda _e: self.root.after(30, lambda: self.clear_combobox_focus(theme_combo, win)))

        follow_var = tk.BooleanVar(value=self.prefs.follow_symlinks)
        hidden_var = tk.BooleanVar(value=self.prefs.include_hidden)
        ignore_empty_var = tk.BooleanVar(value=getattr(self.prefs, "ignore_empty_files_for_groups", True))
        tk.Checkbutton(frame, text=self.t("Follow symbolic links"), variable=follow_var, bg=self.theme["bg"], fg=self.theme["text"], selectcolor=self.theme["surface2"], activebackground=self.theme["bg"], activeforeground=self.theme["text"]).grid(row=2, column=0, columnspan=2, sticky="w", pady=8)
        tk.Label(frame, text=self.t("If enabled, folder shortcuts/symlinks can be followed during recursive scanning. Keep this off unless you need it, because symlinks may point outside the dragged folder or create loops."), bg=self.theme["bg"], fg=self.theme["muted"], wraplength=520, justify="left").grid(row=3, column=0, columnspan=2, sticky="ew")
        tk.Checkbutton(frame, text=self.t("Include hidden files"), variable=hidden_var, bg=self.theme["bg"], fg=self.theme["text"], selectcolor=self.theme["surface2"], activebackground=self.theme["bg"], activeforeground=self.theme["text"]).grid(row=4, column=0, columnspan=2, sticky="w", pady=8)
        tk.Checkbutton(frame, text=self.t("Ignore empty files when grouping duplicates"), variable=ignore_empty_var, bg=self.theme["bg"], fg=self.theme["text"], selectcolor=self.theme["surface2"], activebackground=self.theme["bg"], activeforeground=self.theme["text"]).grid(row=5, column=0, columnspan=2, sticky="w", pady=8)
        tk.Label(frame, text=self.t("When enabled, 0-byte empty files are still listed and hashed, but they are not placed into duplicate groups. This helps avoid accidentally deleting intentional placeholder files such as __init__.py."), bg=self.theme["bg"], fg=self.theme["muted"], wraplength=520, justify="left").grid(row=6, column=0, columnspan=2, sticky="ew")

        info = tk.Label(frame, text=self.t("Settings are saved locally under your user profile."), bg=self.theme["bg"], fg=self.theme["muted"], wraplength=520, justify="left")
        info.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(12, 8))

        row = tk.Frame(frame, bg=self.theme["bg"])
        row.grid(row=8, column=0, columnspan=2, sticky="e", pady=(18, 0))
        def save():
            self.prefs.language = name_to_code.get(lang_var.get(), "en-US")
            self.prefs.theme = theme_options.get(theme_var.get(), "light")
            self.prefs.follow_symlinks = bool(follow_var.get())
            self.prefs.include_hidden = bool(hidden_var.get())
            self.prefs.ignore_empty_files_for_groups = bool(ignore_empty_var.get())
            self.prefs.save()
            self.translator.load(self.prefs.language)
            win.destroy()
            self.build_ui()
            self.recompute_groups()
            self.refresh_tree(keep_selection=True)
            self.set_status(self.t("Settings saved."))
        self._button(row, "Cancel", win.destroy).pack(side=tk.RIGHT, padx=(6, 0))
        self._button(row, "Save", save, primary=True).pack(side=tk.RIGHT)
        self._button(row, "Restore Defaults", lambda: (win.destroy(), self.restore_defaults()), warning=True).pack(side=tk.RIGHT, padx=(0, 8))


    def clear_combobox_focus(self, combo: ttk.Combobox, parent: tk.Widget) -> None:
        try:
            combo.selection_clear()
        except Exception:
            pass
        try:
            parent.focus_set()
        except Exception:
            pass

    def current_log_text(self) -> str:
        if not self.log_file:
            return self.t("No log file is available for this session.")
        try:
            return Path(self.log_file).read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return self.t("Could not read log file: {error}").format(error=str(exc))

    def report_bug(self) -> None:
        LOG.info("Preparing bug report email draft from current session log: %s", self.log_file)
        subject = self.t("HashSieve bug report / feature request")
        log_path = str(self.log_file or "")
        body = self.t("Bug report email body").format(
            app=APP_NAME,
            version=APP_VERSION,
            log_path=log_path,
            os=platform.platform(),
            python=sys.version.replace("\n", " "),
            language=self.prefs.language,
            theme=self.prefs.theme,
            workers=self.prefs.workers,
            file_count=len(self.entries),
            duplicate_groups=self.count_duplicate_groups(),
            duplicate_files=self.count_duplicate_files(),
            log_content=self.current_log_text(),
        )
        url = "mailto:{to}?subject={subject}&body={body}".format(
            to=AUTHOR_EMAIL,
            subject=urllib.parse.quote(subject),
            body=urllib.parse.quote(body),
        )
        webbrowser.open(url)
        self.set_status(self.t("Bug report draft opened. Log file: {path}").format(path=log_path))

    def show_about(self) -> None:
        text = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            + self.t("A local-first Windows desktop tool for calculating file hashes and safely cleaning duplicate files.")
            + "\n\n"
            + f"{self.t('Author')}: {AUTHOR}\n"
            + f"{self.t('Email')}: {AUTHOR_EMAIL}\n"
            + f"GitHub: {GITHUB_URL}\n\n"
            + self.t("Bug reports, feature requests, GitHub stars, and sponsorship are all appreciated. Thank you for supporting the project.")
        )
        messagebox.showinfo(self.t("About"), text, parent=self.root)

    def on_close(self) -> None:
        try:
            self.prefs.window_geometry = self.root.geometry()
            self.prefs.workers = int(self.workers_var.get()) if hasattr(self, "workers_var") else self.prefs.workers
            self.prefs.recycle_bin = bool(self.recycle_var.get()) if hasattr(self, "recycle_var") else self.prefs.recycle_bin
            self.prefs.sort_column = self.sort_column or ""
            self.prefs.sort_reverse = bool(self.sort_reverse)
            self.save_column_state()
            self.prefs.save()
        except Exception:
            pass
        if self.is_busy():
            if not messagebox.askyesno(self.t("Hashing is running"), self.t("Scanning/hashing is still running. Exit anyway?"), parent=self.root):
                return
            self.stop_event.set()
        try:
            logging.shutdown()
        except Exception:
            pass
        self.root.destroy()
