# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import platform
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QAction, QActionGroup, QBrush, QColor, QFont, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMenu,
    QMessageBox, QProgressBar, QPushButton, QSizePolicy, QSpinBox, QStatusBar,
    QTableWidget, QTableWidgetItem, QTableWidgetSelectionRange, QVBoxLayout, QWidget,
)

from .. import config
from ..core.csv_exporter import export_to_csv
from ..core.duplicate_finder import annotate_groups, choose_files_to_delete, summarize
from ..core.file_ops import SEND2TRASH_AVAILABLE, delete_files, open_containing_folder
from ..core.models import DISPLAY_NAMES, HASH_COLUMNS, FileRecord
from ..core.scanner import normalize_path
from ..i18n.translator import DEFAULT_LANGUAGE, Translator
from ..utils.app_logging import get_session_log_file
from ..utils.app_settings import (
    AppSettings, clamp_worker_count, default_worker_count, max_worker_count,
)
from ..utils.formatters import format_duration, format_size
from ..utils.paths import get_assets_dir, get_executable_dir, get_locales_dir
from .styles import build_stylesheet, get_group_color, get_ungrouped_row_color
from .widgets import (
    ROW_BACKGROUND_ROLE, ROW_FOREGROUND_ROLE, NumericTableWidgetItem,
    RowColorDelegate, StatCard,
)
from .workers import HashWorker


KEEP_STRATEGIES = ["first", "oldest", "newest", "shortest_path", "longest_path"]
COLUMNS = [
    ("group", "Group"),
    ("filename", "Filename"),
    ("size", "Size"),
    ("md5", "MD5"),
    ("sha1", "SHA-1"),
    ("crc32", "CRC32"),
    ("sha256", "SHA-256"),
    ("sha384", "SHA-384"),
    ("sha512", "SHA-512"),
    ("extension", "Extension"),
    ("modified_time", "Modified Time"),
    ("created_time", "Created Time"),
    ("duration", "Hashing Duration"),
    ("path", "Full Path"),
    ("error", "Error"),
]
COL_INDEX = {key: idx for idx, (key, _label) in enumerate(COLUMNS)}
DEFAULT_COLUMN_WIDTHS = {
    "group": 90,
    "filename": 260,
    "size": 110,
    "md5": 260,
    "sha1": 300,
    "crc32": 110,
    "sha256": 420,
    "sha384": 520,
    "sha512": 620,
    "extension": 100,
    "modified_time": 170,
    "created_time": 170,
    "duration": 130,
    "path": 650,
    "error": 260,
}

def _mono_font(point_size: int = 9) -> QFont:
    font = QFont()
    font.setFamilies(["Consolas", "Cascadia Mono", "SF Mono", "Menlo", "Courier New"])
    font.setPointSize(point_size)
    return font


class UpdateCheckWorker(QThread):
    result = Signal(bool, str, str, bool)  # has_update, version, error, manual

    def __init__(self, manual: bool, parent=None):
        super().__init__(parent)
        self.manual = manual

    def run(self) -> None:
        try:
            req = urllib.request.Request(config.UPDATE_VERSION_URL, headers={"User-Agent": "HashSieve"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
            latest = str(data.get("version") or data.get("app_version") or "").strip()
            has_update = config.is_newer_version(latest)
            self.result.emit(has_update, latest, "", self.manual)
        except Exception as exc:
            self.result.emit(False, "", str(exc), self.manual)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self.translator = Translator(get_locales_dir(), self.settings.get("language", DEFAULT_LANGUAGE))
        self.theme = self.settings.get("theme", "light")
        self.all_records: List[FileRecord] = []
        self.worker: Optional[HashWorker] = None
        self._processing = False
        self.sort_column: str = self.settings.get("sort_column", "group") or "group"
        self.sort_reverse: bool = bool(self.settings.get("sort_reverse", False))
        self.update_worker: Optional[UpdateCheckWorker] = None
        self._status_key = "Ready. Drag files or folders into the window, or use Add Files / Add Folder."
        self._status_fallback: str | None = None
        self._status_kwargs: dict = {}

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(180)
        self.search_debounce_timer.timeout.connect(self.refresh_table)

        # Arrow clicks and typed values give QSpinBox keyboard focus and select
        # its text. Release that focus shortly after the last change so the
        # worker value does not remain highlighted. Restarting the timer allows
        # rapid repeated clicks before focus is released.
        self.worker_focus_release_timer = QTimer(self)
        self.worker_focus_release_timer.setSingleShot(True)
        self.worker_focus_release_timer.setInterval(220)
        self.worker_focus_release_timer.timeout.connect(self._release_workers_focus)

        self.setAcceptDrops(True)
        self.setMinimumSize(1100, 700)
        self._build_menu_bar()
        self._build_central_widget()
        self._build_status_bar()
        self._connect_shortcuts()
        self._apply_theme()
        self._retranslate_ui()
        self._restore_window_geometry()
        self._restore_table_layout()
        self._update_controls_enabled()
        self._set_status("Ready. Drag files or folders into the window, or use Add Files / Add Folder.")
        self._check_updates(manual=False)

    def t(self, key: str, fallback: str | None = None, **kwargs) -> str:
        return self.translator.t(key, fallback, **kwargs)

    def _set_status(self, key: str, fallback: str | None = None, **kwargs) -> None:
        """Store a translatable status message and render it in the active language."""
        self._status_key = key
        self._status_fallback = fallback
        self._status_kwargs = dict(kwargs)
        if hasattr(self, "status_label"):
            self.status_label.setText(self.t(key, fallback=fallback, **kwargs))

    def _refresh_status(self) -> None:
        if hasattr(self, "status_label"):
            self.status_label.setText(self.t(self._status_key, fallback=self._status_fallback, **self._status_kwargs))

    # UI -----------------------------------------------------------------
    def _build_menu_bar(self) -> None:
        menubar = self.menuBar()
        self.menu_file = menubar.addMenu("")
        self.act_add_files = QAction(self); self.act_add_files.setShortcut(QKeySequence("Ctrl+O")); self.act_add_files.triggered.connect(self.add_files_dialog)
        self.act_add_folder = QAction(self); self.act_add_folder.triggered.connect(self.add_folder_dialog)
        self.act_export_csv = QAction(self); self.act_export_csv.setShortcut(QKeySequence("Ctrl+E")); self.act_export_csv.triggered.connect(self.export_csv)
        self.act_clear_list = QAction(self); self.act_clear_list.triggered.connect(self.clear_list)
        self.act_exit = QAction(self); self.act_exit.setShortcut(QKeySequence("Ctrl+Q")); self.act_exit.triggered.connect(self.close)
        for act in [self.act_add_files, self.act_add_folder]: self.menu_file.addAction(act)
        self.menu_file.addSeparator(); self.menu_file.addAction(self.act_export_csv); self.menu_file.addAction(self.act_clear_list); self.menu_file.addSeparator(); self.menu_file.addAction(self.act_exit)

        self.menu_edit = menubar.addMenu("")
        self.act_select_all = QAction(self); self.act_select_all.triggered.connect(self._select_all_visible)
        self.act_select_duplicates = QAction(self); self.act_select_duplicates.triggered.connect(self.auto_select_duplicates)
        self.menu_edit.addAction(self.act_select_all); self.menu_edit.addAction(self.act_select_duplicates); self.menu_edit.addSeparator()
        self.copy_hash_actions = {}
        for key in HASH_COLUMNS:
            act = QAction(self); act.triggered.connect(lambda _=False, k=key: self.copy_hash(k)); self.copy_hash_actions[key] = act; self.menu_edit.addAction(act)
        self.menu_edit.addSeparator()
        self.act_copy_paths = QAction(self); self.act_copy_paths.triggered.connect(self.copy_paths)
        self.act_copy_rows = QAction(self); self.act_copy_rows.triggered.connect(self.copy_rows)
        self.act_open_location = QAction(self); self.act_open_location.triggered.connect(self.open_selected_location)
        self.act_remove_selected = QAction(self); self.act_remove_selected.triggered.connect(self.remove_selected_from_list)
        self.act_delete_selected = QAction(self); self.act_delete_selected.triggered.connect(self.delete_selected)
        for act in [self.act_copy_paths, self.act_copy_rows, self.act_open_location, self.act_remove_selected, self.act_delete_selected]: self.menu_edit.addAction(act)

        self.menu_view = menubar.addMenu("")
        self.menu_language = self.menu_view.addMenu("")
        self.language_action_group = QActionGroup(self); self.language_action_group.setExclusive(True)
        for lang in self.translator.available_languages():
            act = QAction(self.translator.language_display_name(lang), self); act.setCheckable(True); act.setData(lang); act.setChecked(lang == self.translator.current_language); act.triggered.connect(lambda _=False, lc=lang: self._change_language(lc)); self.language_action_group.addAction(act); self.menu_language.addAction(act)
        self.menu_theme = self.menu_view.addMenu("")
        self.theme_action_group = QActionGroup(self); self.theme_action_group.setExclusive(True)
        self.act_theme_light = QAction(self); self.act_theme_light.setCheckable(True); self.act_theme_light.setChecked(self.theme == "light"); self.act_theme_light.triggered.connect(lambda: self._change_theme("light"))
        self.act_theme_dark = QAction(self); self.act_theme_dark.setCheckable(True); self.act_theme_dark.setChecked(self.theme == "dark"); self.act_theme_dark.triggered.connect(lambda: self._change_theme("dark"))
        for act in [self.act_theme_light, self.act_theme_dark]: self.theme_action_group.addAction(act); self.menu_theme.addAction(act)

        self.menu_tools = menubar.addMenu("")
        self.act_restore_defaults = QAction(self); self.act_restore_defaults.triggered.connect(self.restore_defaults)
        self.act_open_log_folder = QAction(self); self.act_open_log_folder.triggered.connect(self.open_log_folder)
        for act in [self.act_restore_defaults, self.act_open_log_folder]: self.menu_tools.addAction(act)

        self.menu_help = menubar.addMenu("")
        self.act_check_updates = QAction(self); self.act_check_updates.triggered.connect(lambda: self._check_updates(manual=True))
        self.act_github = QAction(self); self.act_github.triggered.connect(lambda: webbrowser.open(config.GITHUB_REPO_URL))
        self.act_report_bug = QAction(self); self.act_report_bug.triggered.connect(self.report_bug)
        self.act_email_author = QAction(self); self.act_email_author.triggered.connect(self.email_author)
        self.act_sponsor = QAction(self); self.act_sponsor.triggered.connect(lambda: webbrowser.open(config.SPONSOR_URL))
        self.act_coffee = QAction(self); self.act_coffee.triggered.connect(lambda: webbrowser.open(config.BUYMEACOFFEE_URL))
        self.act_about = QAction(self); self.act_about.triggered.connect(self.about)
        for act in [self.act_check_updates, self.act_github, self.act_report_bug, self.act_email_author]: self.menu_help.addAction(act)
        self.menu_help.addSeparator(); self.menu_help.addAction(self.act_sponsor); self.menu_help.addAction(self.act_coffee); self.menu_help.addSeparator(); self.menu_help.addAction(self.act_about)

    def _build_central_widget(self) -> None:
        central = QWidget(); central.setObjectName("centralWidget"); self.setCentralWidget(central)
        root = QVBoxLayout(central); root.setContentsMargins(16, 14, 16, 14); root.setSpacing(12)
        root.addWidget(self._build_drop_zone())
        root.addWidget(self._build_progress_area())
        root.addLayout(self._build_stats_row())
        root.addLayout(self._build_filter_row())
        root.addWidget(self._build_table(), stretch=1)
        root.addLayout(self._build_bottom_bar())

    def _build_drop_zone(self) -> QFrame:
        frame = QFrame(); frame.setObjectName("dropZone"); frame.setProperty("dragActive", "false"); frame.setMinimumHeight(128); self.drop_zone_frame = frame
        outer = QVBoxLayout(frame); outer.setContentsMargins(20, 14, 20, 14); outer.setSpacing(10)
        top = QHBoxLayout(); top.setSpacing(14)
        self.drop_icon = QLabel(); self.drop_icon.setObjectName("dropZoneIcon")
        logo_path = get_assets_dir() / "hashsieve_logo.png"
        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                self.drop_icon.setPixmap(pix.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.drop_icon.setText("HashSieve")
        else:
            self.drop_icon.setText("HashSieve")
        top.addWidget(self.drop_icon, 0, Qt.AlignTop)
        text = QVBoxLayout(); text.setSpacing(3); self.drop_zone_title_label = QLabel(); self.drop_zone_title_label.setObjectName("dropZoneTitle"); self.drop_zone_subtitle_label = QLabel(); self.drop_zone_subtitle_label.setObjectName("dropZoneSubtitle"); self.drop_zone_subtitle_label.setWordWrap(True); text.addWidget(self.drop_zone_title_label); text.addWidget(self.drop_zone_subtitle_label); top.addLayout(text, stretch=1)
        btn_col = QVBoxLayout(); btn_col.setSpacing(8)
        self.add_files_btn = QPushButton(); self.add_files_btn.setProperty("class", "primary"); self.add_files_btn.clicked.connect(self.add_files_dialog)
        self.add_folder_btn = QPushButton(); self.add_folder_btn.clicked.connect(self.add_folder_dialog)
        btn_col.addWidget(self.add_files_btn); btn_col.addWidget(self.add_folder_btn); top.addLayout(btn_col)
        outer.addLayout(top)
        opts = QHBoxLayout(); opts.setSpacing(16)
        self.follow_symlinks_checkbox = QCheckBox(); self.follow_symlinks_checkbox.setChecked(bool(self.settings.get("follow_symlinks", False)))
        self.include_hidden_checkbox = QCheckBox(); self.include_hidden_checkbox.setChecked(bool(self.settings.get("include_hidden", False)))
        self.ignore_empty_checkbox = QCheckBox(); self.ignore_empty_checkbox.setChecked(bool(self.settings.get("ignore_empty_grouping", True)))
        self.recycle_checkbox = QCheckBox(); self.recycle_checkbox.setChecked(bool(self.settings.get("use_recycle_bin", True)))
        self.workers_label = QLabel(); self.workers_spin = QSpinBox(); self.workers_spin.setRange(1, max_worker_count()); self.workers_spin.setKeyboardTracking(False); self.workers_spin.setAccelerated(True); self.workers_spin.setMinimumWidth(94); self.workers_spin.setValue(clamp_worker_count(self.settings.get("workers", default_worker_count())))
        self.follow_symlinks_checkbox.stateChanged.connect(lambda _=0: self._sync_surface_settings())
        self.include_hidden_checkbox.stateChanged.connect(lambda _=0: self._sync_surface_settings())
        self.recycle_checkbox.stateChanged.connect(lambda _=0: self._sync_surface_settings())
        self.ignore_empty_checkbox.stateChanged.connect(lambda _=0: self._on_grouping_setting_changed())
        self.workers_spin.valueChanged.connect(lambda _=0: self._on_workers_changed())
        self.workers_spin.editingFinished.connect(self._on_workers_editing_finished)
        for w in [self.follow_symlinks_checkbox, self.include_hidden_checkbox, self.ignore_empty_checkbox, self.recycle_checkbox]: opts.addWidget(w)
        opts.addStretch(1); opts.addWidget(self.workers_label); opts.addWidget(self.workers_spin)
        outer.addLayout(opts)
        return frame

    def _build_progress_area(self) -> QWidget:
        widget = QWidget(); layout = QHBoxLayout(widget); layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(10)
        self.progress_bar = QProgressBar(); self.progress_bar.setTextVisible(False); self.progress_bar.setFixedHeight(10); layout.addWidget(self.progress_bar, stretch=1)
        self.cancel_btn = QPushButton(); self.cancel_btn.clicked.connect(self._cancel_processing); layout.addWidget(self.cancel_btn)
        self.progress_area = widget; widget.setVisible(False); return widget

    def _build_stats_row(self) -> QHBoxLayout:
        layout = QHBoxLayout(); layout.setSpacing(10)
        self.stat_total_files = StatCard(""); self.stat_total_size = StatCard(""); self.stat_duplicate_groups = StatCard(""); self.stat_duplicate_files = StatCard(""); self.stat_reclaimable = StatCard("", danger=True)
        for card in [self.stat_total_files, self.stat_total_size, self.stat_duplicate_groups, self.stat_duplicate_files, self.stat_reclaimable]: layout.addWidget(card, stretch=1)
        return layout

    def _build_filter_row(self) -> QHBoxLayout:
        layout = QHBoxLayout(); layout.setSpacing(10)
        self.search_label = QLabel(); layout.addWidget(self.search_label)
        self.search_box = QLineEdit(); self.search_box.textChanged.connect(lambda _text: self.search_debounce_timer.start()); layout.addWidget(self.search_box, stretch=1)
        self.show_duplicates_only_checkbox = QCheckBox(); self.show_duplicates_only_checkbox.setChecked(bool(self.settings.get("show_duplicates_only", False))); self.show_duplicates_only_checkbox.stateChanged.connect(lambda _: (self.settings.set("show_duplicates_only", self.show_duplicates_only_checkbox.isChecked()), self.refresh_table()))
        layout.addWidget(self.show_duplicates_only_checkbox)
        self.keep_strategy_label = QLabel(); layout.addWidget(self.keep_strategy_label)
        self.keep_strategy_combo = QComboBox(); self._rebuild_keep_strategy_combo(self.settings.get("keep_strategy", "first")); self.keep_strategy_combo.currentIndexChanged.connect(lambda _=0: self._sync_surface_settings()); layout.addWidget(self.keep_strategy_combo)
        self.auto_select_btn = QPushButton(); self.auto_select_btn.setProperty("class", "primary"); self.auto_select_btn.clicked.connect(self.auto_select_duplicates); layout.addWidget(self.auto_select_btn)
        return layout

    def _build_table(self) -> QTableWidget:
        table = QTableWidget(0, len(COLUMNS)); table.setSelectionBehavior(QAbstractItemView.SelectRows); table.setSelectionMode(QAbstractItemView.ExtendedSelection); table.setEditTriggers(QAbstractItemView.NoEditTriggers); table.setAlternatingRowColors(False); table.setSortingEnabled(False); table.verticalHeader().setVisible(False); table.setContextMenuPolicy(Qt.CustomContextMenu); table.customContextMenuRequested.connect(self._show_context_menu); table.cellDoubleClicked.connect(lambda row, _col: self.open_record_location(row)); table.itemSelectionChanged.connect(self._on_selection_changed)
        header = table.horizontalHeader(); header.setSectionsMovable(True); header.setStretchLastSection(False); header.setSortIndicatorShown(False); header.sectionClicked.connect(self._on_header_clicked); header.sectionMoved.connect(lambda *_: self._save_table_layout()); header.sectionResized.connect(lambda *_: self._save_table_layout())
        for i in range(len(COLUMNS)): header.setSectionResizeMode(i, QHeaderView.Interactive)
        for key, idx in COL_INDEX.items():
            table.setColumnWidth(idx, DEFAULT_COLUMN_WIDTHS.get(key, 160))
        # Explicit delegate painting is used so full-row group backgrounds are
        # not overridden by Windows/Qt style-sheet item rendering.
        self.row_color_delegate = RowColorDelegate(lambda: self.theme, table)
        table.setItemDelegate(self.row_color_delegate)
        self.table = table
        return table

    def _build_bottom_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout(); layout.setSpacing(10)
        self.status_label = QLabel(); self.status_label.setProperty("class", "muted"); self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred); layout.addWidget(self.status_label, stretch=1)
        self.clear_btn = QPushButton(); self.clear_btn.clicked.connect(self.clear_list); layout.addWidget(self.clear_btn)
        self.export_csv_btn = QPushButton(); self.export_csv_btn.clicked.connect(self.export_csv); layout.addWidget(self.export_csv_btn)
        self.delete_selected_btn = QPushButton(); self.delete_selected_btn.setProperty("class", "danger"); self.delete_selected_btn.clicked.connect(self.delete_selected); layout.addWidget(self.delete_selected_btn)
        return layout

    def _build_status_bar(self) -> None:
        bar = QStatusBar()
        bar.setSizeGripEnabled(False)
        self.setStatusBar(bar)
        bar.hide()

    def _connect_shortcuts(self) -> None:
        delete_shortcut = QShortcut(QKeySequence("Delete"), self.table)
        delete_shortcut.activated.connect(self.delete_selected)
        select_shortcut = QShortcut(QKeySequence("Ctrl+A"), self.table)
        select_shortcut.activated.connect(self._select_all_visible)
        copy_shortcut = QShortcut(QKeySequence.Copy, self.table)
        copy_shortcut.activated.connect(self.copy_rows)

    # translation/theme --------------------------------------------------
    def _rebuild_keep_strategy_combo(self, select_key: Optional[str] = None) -> None:
        if not hasattr(self, "keep_strategy_combo"):
            return
        current = select_key or self.keep_strategy_combo.currentData() or "first"
        self.keep_strategy_combo.blockSignals(True); self.keep_strategy_combo.clear()
        labels = {"first": "Keep first file in each group", "oldest": "Keep oldest modified file", "newest": "Keep newest modified file", "shortest_path": "Keep shortest path", "longest_path": "Keep longest path"}
        for key in KEEP_STRATEGIES:
            self.keep_strategy_combo.addItem(self.t(labels[key], fallback=labels[key]), key)
        idx = self.keep_strategy_combo.findData(current)
        if idx >= 0: self.keep_strategy_combo.setCurrentIndex(idx)
        self.keep_strategy_combo.blockSignals(False)

    def _label_for_column(self, key: str) -> str:
        label = dict(COLUMNS).get(key, key)
        text = self.t(label, fallback=label)
        if key == self.sort_column:
            text += " ▲" if not self.sort_reverse else " ▼"
        return text

    def _update_headers(self) -> None:
        self.table.setHorizontalHeaderLabels([self._label_for_column(k) for k, _ in COLUMNS])

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(f"{config.APP_NAME} {config.APP_VERSION}")
        self.menu_file.setTitle(self.t("File")); self.act_add_files.setText(self.t("Add Files")); self.act_add_folder.setText(self.t("Add Folder")); self.act_export_csv.setText(self.t("Export CSV")); self.act_clear_list.setText(self.t("Clear List")); self.act_exit.setText(self.t("Exit"))
        self.menu_edit.setTitle(self.t("Edit")); self.act_select_all.setText(self.t("Select All Visible")); self.act_select_duplicates.setText(self.t("Select duplicates except one"));
        for key, act in self.copy_hash_actions.items(): act.setText(self.t("Copy", fallback="Copy") + f" {DISPLAY_NAMES[key]}")
        self.act_copy_paths.setText(self.t("Copy Selected Paths")); self.act_copy_rows.setText(self.t("Copy Selected Rows")); self.act_open_location.setText(self.t("Open File Location")); self.act_remove_selected.setText(self.t("Remove Selected from List")); self.act_delete_selected.setText(self.t("Delete Selected"))
        self.menu_view.setTitle(self.t("View", fallback="View")); self.menu_language.setTitle(self.t("Language")); self.menu_theme.setTitle(self.t("Theme", fallback="Theme")); self.act_theme_light.setText(self.t("Light")); self.act_theme_dark.setText(self.t("Dark"))
        self.menu_tools.setTitle(self.t("Tools", fallback="Tools")); self.act_restore_defaults.setText(self.t("Restore Defaults")); self.act_open_log_folder.setText(self.t("Open Log Folder"))
        self.menu_help.setTitle(self.t("Help")); self.act_check_updates.setText(self.t("Check for Updates")); self.act_github.setText(self.t("GitHub Repository")); self.act_report_bug.setText(self.t("Report Bug / Request Feature")); self.act_email_author.setText(self.t("Email Author")); self.act_sponsor.setText(self.t("GitHub Sponsors")); self.act_coffee.setText(self.t("Buy Me a Coffee")); self.act_about.setText(self.t("About"))
        self.drop_zone_title_label.setText(self.t("HashSieve — recursive hash and duplicate-file cleaner")); self.drop_zone_subtitle_label.setText(self.t("Drop one or more files/folders here. Subfolders will be scanned recursively.")); self.add_files_btn.setText("📄 " + self.t("Add Files")); self.add_folder_btn.setText("📁 " + self.t("Add Folder"))
        self.follow_symlinks_checkbox.setText(self.t("Follow symbolic links")); self.include_hidden_checkbox.setText(self.t("Include hidden files")); self.ignore_empty_checkbox.setText(self.t("Ignore empty files when grouping duplicates")); self.recycle_checkbox.setText(self.t("Move to Recycle Bin")); self.workers_label.setText(self.t("Workers", fallback="Workers")); self.cancel_btn.setText(self.t("Stop"))
        self.stat_total_files.set_caption(self.t("Files", fallback="Files")); self.stat_total_size.set_caption(self.t("Size")); self.stat_duplicate_groups.set_caption(self.t("Duplicate groups", fallback="Duplicate groups")); self.stat_duplicate_files.set_caption(self.t("Duplicate files", fallback="Duplicate files")); self.stat_reclaimable.set_caption(self.t("Reclaimable", fallback="Reclaimable"))
        self.search_label.setText(self.t("Search/filter:")); self.search_box.setPlaceholderText(self.t("Search/filter:", fallback="Search/filter:")); self.show_duplicates_only_checkbox.setText(self.t("Duplicates only")); self.keep_strategy_label.setText(self.t("Keep", fallback="Keep")); self._rebuild_keep_strategy_combo(); self.auto_select_btn.setText("✨ " + self.t("Select duplicates except one"))
        self.clear_btn.setText(self.t("Clear List")); self.export_csv_btn.setText("⬇ " + self.t("Export CSV")); self.delete_selected_btn.setText("🗑 " + self.t("Delete Selected")); self._update_headers(); self._update_stats()

    def _change_language(self, lang_code: str) -> None:
        self.translator.set_language(lang_code); self.settings.set("language", lang_code); self._sync_language_theme_actions(); self._retranslate_ui(); self.refresh_table(); self._refresh_status()

    def _change_theme(self, theme: str) -> None:
        self.theme = theme; self.settings.set("theme", theme); self._sync_language_theme_actions(); self._apply_theme(); self.refresh_table()

    def _apply_theme(self) -> None:
        self.setStyleSheet(build_stylesheet(self.theme, get_assets_dir()))

    # drag/drop ----------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if self._processing:
            event.ignore(); return
        if event.mimeData().hasUrls():
            event.acceptProposedAction(); self._set_drop_zone_active(True)

    def dragLeaveEvent(self, event) -> None:
        self._set_drop_zone_active(False)

    def dropEvent(self, event) -> None:
        self._set_drop_zone_active(False)
        if self._processing:
            event.ignore(); return
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
        if paths: self._start_processing(paths)
        event.acceptProposedAction()

    def _set_drop_zone_active(self, active: bool) -> None:
        self.drop_zone_frame.setProperty("dragActive", "true" if active else "false"); self.drop_zone_frame.style().unpolish(self.drop_zone_frame); self.drop_zone_frame.style().polish(self.drop_zone_frame)

    # files --------------------------------------------------------------
    def add_files_dialog(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, self.t("Select files"))
        if files: self._start_processing(files)

    def add_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.t("Select folder"))
        if folder: self._start_processing([folder])

    def _start_processing(self, paths: List[str]) -> None:
        if self._processing:
            QMessageBox.information(self, config.APP_NAME, self.t("Busy now. Please wait until scanning/hashing finishes before adding more files or folders.")); return
        self._processing = True; self._set_controls_enabled(False); self.progress_area.setVisible(True); self.progress_bar.setRange(0, 0); self._set_status("Scanning files recursively...")
        self.settings.set_many({"follow_symlinks": self.follow_symlinks_checkbox.isChecked(), "include_hidden": self.include_hidden_checkbox.isChecked(), "ignore_empty_grouping": self.ignore_empty_checkbox.isChecked(), "use_recycle_bin": self.recycle_checkbox.isChecked(), "workers": self.workers_spin.value()})
        self.worker = HashWorker(paths, follow_symlinks=self.follow_symlinks_checkbox.isChecked(), include_hidden=self.include_hidden_checkbox.isChecked(), ignore_empty_grouping=self.ignore_empty_checkbox.isChecked(), max_workers=self.workers_spin.value())
        self.worker.scan_progress.connect(self._on_scan_progress); self.worker.hash_progress.connect(self._on_hash_progress); self.worker.finished_all.connect(self._on_worker_finished); self.worker.failed.connect(self._on_worker_failed); self.worker.start()

    def _cancel_processing(self) -> None:
        if self.worker: self.worker.cancel(); self._set_status("Hashing stopped. Completed {done}/{total} file(s).", fallback="Stopping...", done=0, total=0); self.progress_bar.setRange(0, 1); self.progress_bar.setValue(0)

    def _on_scan_progress(self, count: int, size: int, _path: str) -> None:
        self._set_status("Scanning files: {count} found, {size} total...", count=count, size=format_size(size))

    def _on_hash_progress(self, done: int, total: int, bytes_done: int, bytes_total: int, fps: float, bps: float) -> None:
        if self.progress_bar.maximum() == 0: self.progress_bar.setRange(0, max(1, total))
        self.progress_bar.setValue(done)
        if bytes_total:
            pct = min(100.0, bytes_done * 100.0 / bytes_total)
            self._set_status("Hashing progress: {done}/{total} file(s), {bytes_done}/{bytes_total} ({percent:.1f}%). Speed: {files_per_sec:.2f} files/s, {bytes_per_sec}/s.", done=done, total=total, bytes_done=format_size(bytes_done), bytes_total=format_size(bytes_total), percent=pct, files_per_sec=fps, bytes_per_sec=format_size(bps))
        else:
            self._set_status("Hashing progress: {done}/{total} file(s), {bytes_done}/{bytes_total}. Speed: {files_per_sec:.2f} files/s, {bytes_per_sec}/s.", done=done, total=total, bytes_done=format_size(bytes_done), bytes_total=format_size(bytes_total), files_per_sec=fps, bytes_per_sec=format_size(bps))

    def _on_worker_finished(self, new_records, errors, was_cancelled: bool, elapsed: float) -> None:
        self._processing = False; self.progress_area.setVisible(False); self._set_controls_enabled(True)
        existing = {normalize_path(Path(r.path)) for r in self.all_records}
        to_add = [r for r in new_records if normalize_path(Path(r.path)) not in existing]
        self.all_records.extend(to_add)
        annotate_groups(self.all_records, ignore_empty_grouping=self.ignore_empty_checkbox.isChecked())
        self.refresh_table()
        summary = summarize(self.all_records)
        if was_cancelled:
            self._set_status("Hashing stopped. Completed {done}/{total} file(s).", done=len(to_add), total=len(new_records))
        else:
            self._set_status("Hashing complete. Found {groups} duplicate group(s), {dupes} duplicate file(s).", groups=summary["duplicate_group_count"], dupes=summary["duplicate_file_count"])
        if errors:
            QMessageBox.warning(self, self.t("Warning", fallback="Warning"), self.t("Some files could not be read", fallback="Some files could not be read") + f": {len(errors)}")
        self.worker = None

    def _on_worker_failed(self, message: str) -> None:
        self._processing = False; self.progress_area.setVisible(False); self._set_controls_enabled(True); QMessageBox.critical(self, self.t("Error"), message); self.worker = None

    def _set_controls_enabled(self, enabled: bool) -> None:
        for w in [self.add_files_btn, self.add_folder_btn, self.follow_symlinks_checkbox, self.include_hidden_checkbox, self.ignore_empty_checkbox, self.recycle_checkbox, self.workers_spin, self.clear_btn, self.export_csv_btn, self.delete_selected_btn, self.auto_select_btn]: w.setEnabled(enabled)

    def _update_controls_enabled(self) -> None:
        self._set_controls_enabled(not self._processing)

    # table --------------------------------------------------------------
    def _apply_filters(self, records: List[FileRecord]) -> List[FileRecord]:
        out = records
        if self.show_duplicates_only_checkbox.isChecked(): out = [r for r in out if r.is_duplicate]
        q = self.search_box.text().strip().lower()
        if q: out = [r for r in out if q in r.filename.lower() or q in r.path.lower()]
        return out

    def _sort_key(self, r: FileRecord):
        c = self.sort_column
        if c == "group": return (0, r.group_id) if r.is_duplicate else (1, 10**12)
        if c == "filename": return r.filename.lower()
        if c == "size": return r.size
        if c in HASH_COLUMNS: return r.hashes.get(c, "")
        if c == "extension": return r.extension
        if c == "modified_time": return r.modified_time
        if c == "created_time": return r.created_time
        if c == "duration": return r.duration_seconds
        if c == "path": return r.path.lower()
        if c == "error": return r.error
        return r.path.lower()

    def _sorted_records(self, records: List[FileRecord]) -> List[FileRecord]:
        if self.sort_column == "group":
            return sorted(records, key=lambda r: ((0 if r.is_duplicate else 1), (-r.group_id if self.sort_reverse else r.group_id), r.path.lower()))
        return sorted(records, key=self._sort_key, reverse=self.sort_reverse)

    def refresh_table(self) -> None:
        filtered = self._sorted_records(self._apply_filters(self.all_records))
        table = self.table
        table.setUpdatesEnabled(False)
        try:
            table.clearSelection()
            table.clearContents()
            table.setRowCount(len(filtered))
            ungrouped_index = 0
            for row, rec in enumerate(filtered):
                self._populate_row(row, rec, ungrouped_index)
                if not rec.is_duplicate:
                    ungrouped_index += 1
        finally:
            table.setUpdatesEnabled(True)
            table.viewport().update()
        self._update_headers()
        self._update_stats()
        self._update_status_bar(len(filtered))

    def _item(self, text: str, data=None, mono: bool = False, align=None, rec: FileRecord | None = None) -> QTableWidgetItem:
        item = NumericTableWidgetItem(text, data if data is not None else text)
        if mono: item.setFont(_mono_font())
        if align is not None: item.setTextAlignment(align)
        if rec is not None: item.setData(Qt.UserRole, rec)
        return item

    def _populate_row(self, row: int, rec: FileRecord, ungrouped_index: int = 0) -> None:
        t = self.table
        group_text = f"#{rec.group_id} ({rec.duplicate_count})" if rec.is_duplicate else "—"
        t.setItem(row, COL_INDEX["group"], self._item(group_text, rec.group_id if rec.is_duplicate else 10**12, align=Qt.AlignCenter, rec=rec))
        t.setItem(row, COL_INDEX["filename"], self._item(rec.filename, rec.filename.lower()))
        t.setItem(row, COL_INDEX["size"], self._item(format_size(rec.size), rec.size, mono=True, align=Qt.AlignRight | Qt.AlignVCenter))
        for key in HASH_COLUMNS:
            t.setItem(row, COL_INDEX[key], self._item(rec.hashes.get(key, ""), rec.hashes.get(key, ""), mono=True))
        t.setItem(row, COL_INDEX["extension"], self._item(rec.extension, rec.extension))
        t.setItem(row, COL_INDEX["modified_time"], self._item(rec.modified_time, rec.modified_time))
        t.setItem(row, COL_INDEX["created_time"], self._item(rec.created_time, rec.created_time))
        t.setItem(row, COL_INDEX["duration"], self._item(format_duration(rec.duration_seconds), rec.duration_seconds, mono=True, align=Qt.AlignRight | Qt.AlignVCenter))
        t.setItem(row, COL_INDEX["path"], self._item(rec.path, rec.path.lower()))
        t.setItem(row, COL_INDEX["error"], self._item(rec.error, rec.error))

        if rec.is_duplicate:
            bg, fg = get_group_color(self.theme, rec.group_id)
        else:
            bg, fg = get_ungrouped_row_color(self.theme, ungrouped_index)
        background = QColor(bg)
        foreground = QColor(fg)
        background_brush = QBrush(background)
        foreground_brush = QBrush(foreground)
        for col in range(t.columnCount()):
            item = t.item(row, col)
            if item is not None:
                # Keep the standard item roles as a fallback and also provide
                # explicit custom roles for RowColorDelegate. The foreground is
                # intentionally neutral; only the background identifies groups.
                item.setBackground(background_brush)
                item.setForeground(foreground_brush)
                item.setData(ROW_BACKGROUND_ROLE, bg)
                item.setData(ROW_FOREGROUND_ROLE, fg)

    def _on_header_clicked(self, visual_or_logical: int) -> None:
        logical = visual_or_logical
        key = COLUMNS[logical][0]
        if self.sort_column == key: self.sort_reverse = not self.sort_reverse
        else: self.sort_column = key; self.sort_reverse = False
        self.settings.set_many({"sort_column": self.sort_column, "sort_reverse": self.sort_reverse})
        self.refresh_table()

    def _update_stats(self) -> None:
        s = summarize(self.all_records)
        self.stat_total_files.set_value(f"{s['total_files']:,}"); self.stat_total_size.set_value(format_size(s["total_size"])); self.stat_duplicate_groups.set_value(f"{s['duplicate_group_count']:,}"); self.stat_duplicate_files.set_value(f"{s['duplicate_file_count']:,}"); self.stat_reclaimable.set_value(format_size(s["reclaimable_space"]))

    def _update_status_bar(self, shown: Optional[int] = None) -> None:
        # The main statistics are already shown in the cards above the table.
        # Keep the native QStatusBar hidden to avoid duplicated/stale summary text.
        return

    # selection/actions --------------------------------------------------
    def _select_all_visible(self) -> None: self.table.selectAll()
    def _selected_records(self) -> List[FileRecord]:
        out = []
        for row in sorted({i.row() for i in self.table.selectedIndexes()}):
            item = self.table.item(row, COL_INDEX["group"]) or self.table.item(row, COL_INDEX["filename"])
            if item: out.append(item.data(Qt.UserRole))
        return [r for r in out if r is not None]

    def auto_select_duplicates(self) -> None:
        to_delete = choose_files_to_delete(self.all_records, self.keep_strategy_combo.currentData() or "first")
        paths = {r.path for r in to_delete}
        cols = self.table.columnCount()
        self.table.blockSignals(True)
        self.table.clearSelection()
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_INDEX["group"])
            rec = item.data(Qt.UserRole) if item else None
            if rec and rec.path in paths:
                self.table.setRangeSelected(QTableWidgetSelectionRange(row, 0, row, cols - 1), True)
        self.table.blockSignals(False)
        self._on_selection_changed()
        if paths:
            self._set_status("Selected {count} duplicate copy/copies while keeping one file in each group. You can Ctrl-click to adjust the selection before deleting.", count=len(paths))

    def copy_hash(self, key: str) -> None:
        records = self._selected_records()
        if not records: return
        QApplication.clipboard().setText("\n".join(r.hashes.get(key, "") for r in records))
        self._set_status("Copied to clipboard.")

    def copy_paths(self) -> None:
        records = self._selected_records(); QApplication.clipboard().setText("\n".join(r.path for r in records)); self._set_status("Copied to clipboard.")

    def copy_rows(self) -> None:
        rows = []
        for r in self._selected_records():
            values = [str(r.group_id if r.is_duplicate else ""), r.filename, str(r.size)] + [r.hashes.get(k, "") for k in HASH_COLUMNS] + [r.extension, r.modified_time, r.created_time, format_duration(r.duration_seconds), r.path, r.error]
            rows.append("\t".join(values))
        QApplication.clipboard().setText("\n".join(rows)); self._set_status("Copied to clipboard.")

    def open_record_location(self, row: int) -> None:
        item = self.table.item(row, COL_INDEX["group"])
        if item and item.data(Qt.UserRole): open_containing_folder(item.data(Qt.UserRole).path)

    def open_selected_location(self) -> None:
        records = self._selected_records()
        if records: open_containing_folder(records[0].path)

    def remove_selected_from_list(self) -> None:
        paths = {r.path for r in self._selected_records()}
        if not paths: return
        self.all_records = [r for r in self.all_records if r.path not in paths]
        annotate_groups(self.all_records, ignore_empty_grouping=self.ignore_empty_checkbox.isChecked())
        self.refresh_table()

    def delete_selected(self) -> None:
        records = self._selected_records()
        if not records:
            QMessageBox.information(self, self.t("Nothing to delete"), self.t("No files are selected for deletion.")); return
        use_recycle = self.recycle_checkbox.isChecked()
        if use_recycle and not SEND2TRASH_AVAILABLE:
            QMessageBox.warning(self, self.t("Recycle bin unavailable"), self.t("Recycle bin unavailable")); return
        total = sum(r.size for r in records); mode = self.t("Recycle bin") if use_recycle else self.t("Permanent delete")
        msg = self.t("Delete {count} file(s), total {size}?\n\nMode: {mode}\n\nThis action changes files on disk.", count=len(records), size=format_size(total), mode=mode)
        if QMessageBox.warning(self, self.t("Confirm deletion"), msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No) != QMessageBox.Yes: return
        ok, failed = delete_files([r.path for r in records], use_recycle_bin=use_recycle); okset = set(ok); self.all_records = [r for r in self.all_records if r.path not in okset]
        annotate_groups(self.all_records, ignore_empty_grouping=self.ignore_empty_checkbox.isChecked()); self.refresh_table(); QMessageBox.information(self, self.t("Delete Selected"), self.t("Deleted {deleted} file(s). Failed: {failed}.", deleted=len(ok), failed=len(failed)))

    def export_csv(self) -> None:
        if not self.all_records:
            QMessageBox.information(self, self.t("No data"), self.t("No data")); return
        default = Path(self.settings.get("last_export_dir") or str(Path.home())) / "HashSieve_export.csv"
        path, _ = QFileDialog.getSaveFileName(self, self.t("Export CSV"), str(default), "CSV (*.csv)")
        if not path: return
        try:
            n = export_to_csv(self.all_records, path); self.settings.set("last_export_dir", str(Path(path).parent)); QMessageBox.information(self, self.t("Export CSV"), self.t("CSV exported: {path}", path=path))
        except Exception as exc: QMessageBox.critical(self, self.t("Export failed"), str(exc))

    def clear_list(self) -> None:
        if self.all_records and QMessageBox.question(self, self.t("Clear List"), self.t("Remove all rows from the list? This does not delete files from disk.")) != QMessageBox.Yes: return
        self.all_records = []; self.search_box.clear(); self.refresh_table(); self._set_status("List cleared.")

    def _show_context_menu(self, pos) -> None:
        if not self._selected_records(): return
        menu = QMenu(self); actions = {}
        for k in HASH_COLUMNS: actions[menu.addAction(self.t("Copy", fallback="Copy") + f" {DISPLAY_NAMES[k]}")] = lambda kk=k: self.copy_hash(kk)
        menu.addSeparator(); actions[menu.addAction(self.t("Copy Selected Paths"))] = self.copy_paths; actions[menu.addAction(self.t("Copy Selected Rows"))] = self.copy_rows
        menu.addSeparator(); actions[menu.addAction(self.t("Open File Location"))] = self.open_selected_location; actions[menu.addAction(self.t("Remove Selected from List"))] = self.remove_selected_from_list; actions[menu.addAction(self.t("Delete Selected"))] = self.delete_selected
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen in actions: actions[chosen]()

    def _sync_surface_settings(self) -> None:
        if not hasattr(self, "follow_symlinks_checkbox"):
            return
        self.settings.set_many({
            "follow_symlinks": self.follow_symlinks_checkbox.isChecked(),
            "include_hidden": self.include_hidden_checkbox.isChecked(),
            "ignore_empty_grouping": self.ignore_empty_checkbox.isChecked(),
            "use_recycle_bin": self.recycle_checkbox.isChecked(),
            "workers": self.workers_spin.value(),
            "show_duplicates_only": self.show_duplicates_only_checkbox.isChecked() if hasattr(self, "show_duplicates_only_checkbox") else False,
            "keep_strategy": self.keep_strategy_combo.currentData() if hasattr(self, "keep_strategy_combo") else "first",
        })

    def _on_grouping_setting_changed(self) -> None:
        self._sync_surface_settings()
        annotate_groups(self.all_records, ignore_empty_grouping=self.ignore_empty_checkbox.isChecked())
        self.refresh_table()

    def _on_workers_changed(self) -> None:
        value = clamp_worker_count(self.workers_spin.value())
        if self.workers_spin.value() != value:
            self.workers_spin.blockSignals(True)
            self.workers_spin.setValue(value)
            self.workers_spin.blockSignals(False)
        self.settings.set("workers", value)
        self.worker_focus_release_timer.start()

    def _on_workers_editing_finished(self) -> None:
        value = clamp_worker_count(self.workers_spin.value())
        if self.workers_spin.value() != value:
            self.workers_spin.blockSignals(True)
            self.workers_spin.setValue(value)
            self.workers_spin.blockSignals(False)
        self.settings.set("workers", value)
        self.worker_focus_release_timer.start(0)

    def _release_workers_focus(self) -> None:
        """Remove focus and text selection from the worker-count editor."""
        line_edit = self.workers_spin.lineEdit()
        if line_edit is not None:
            line_edit.deselect()
        self.workers_spin.clearFocus()

    def _apply_settings_to_surface(self) -> None:
        vals = self.settings.as_dict()
        for widget in [self.follow_symlinks_checkbox, self.include_hidden_checkbox, self.ignore_empty_checkbox, self.recycle_checkbox, self.show_duplicates_only_checkbox, self.workers_spin, self.keep_strategy_combo]:
            widget.blockSignals(True)
        self.follow_symlinks_checkbox.setChecked(bool(vals["follow_symlinks"]))
        self.include_hidden_checkbox.setChecked(bool(vals["include_hidden"]))
        self.ignore_empty_checkbox.setChecked(bool(vals["ignore_empty_grouping"]))
        self.recycle_checkbox.setChecked(bool(vals["use_recycle_bin"]))
        self.show_duplicates_only_checkbox.setChecked(bool(vals["show_duplicates_only"]))
        self.workers_spin.setValue(clamp_worker_count(vals["workers"]))
        self._rebuild_keep_strategy_combo(vals["keep_strategy"])
        for widget in [self.follow_symlinks_checkbox, self.include_hidden_checkbox, self.ignore_empty_checkbox, self.recycle_checkbox, self.show_duplicates_only_checkbox, self.workers_spin, self.keep_strategy_combo]:
            widget.blockSignals(False)
        # Apply the remaining built-in defaults directly. Calling the normal
        # language/theme handlers here would rebuild a large result table more
        # than once; Restore Defaults should perform only one final refresh.
        self.theme = str(vals["theme"])
        self.translator.set_language(str(vals["language"]))
        self.sort_column = str(vals["sort_column"] or "group")
        self.sort_reverse = bool(vals["sort_reverse"])
        self.resize(int(vals["window_width"]), int(vals["window_height"]))
        self._restore_builtin_table_layout()
        self._sync_language_theme_actions()
        self._apply_theme()
        self._retranslate_ui()
        self._sync_surface_settings()
        self._release_workers_focus()

    def _sync_language_theme_actions(self) -> None:
        if hasattr(self, "language_action_group"):
            for act in self.language_action_group.actions():
                act.setChecked(act.data() == self.translator.current_language)
        if hasattr(self, "act_theme_light"):
            self.act_theme_light.setChecked(self.theme == "light")
            self.act_theme_dark.setChecked(self.theme == "dark")

    def _on_selection_changed(self) -> None:
        records = self._selected_records()
        count = len(records)
        if count == 0:
            self._refresh_status()
            return
        dupes = sum(1 for r in records if r.is_duplicate)
        size = sum(r.size for r in records)
        self.status_label.setText(self.t("Selected {count} row(s). Duplicate copies selected: {dupes}. Selected size: {size}.", count=count, dupes=dupes, size=format_size(size)))

    # settings/help ------------------------------------------------------

    def restore_defaults(self) -> None:
        if QMessageBox.question(self, self.t("Restore Defaults"), self.t("Restore all settings to their default values?")) != QMessageBox.Yes:
            return
        self.settings.reset_defaults()
        self._apply_settings_to_surface()
        annotate_groups(self.all_records, ignore_empty_grouping=self.ignore_empty_checkbox.isChecked())
        self.refresh_table()
        self._set_status("Default settings restored.")

    def open_log_folder(self) -> None:
        p = get_session_log_file(); folder = p.parent if p else get_executable_dir(); webbrowser.open(folder.as_uri())

    def email_author(self) -> None:
        url = f"mailto:{config.AUTHOR_EMAIL}?subject={urllib.parse.quote(config.EMAIL_SUBJECT_DEFAULT)}"
        webbrowser.open(url)

    def report_bug(self) -> None:
        log_path = get_session_log_file(); content = ""
        if log_path and log_path.exists():
            try: content = log_path.read_text(encoding="utf-8", errors="replace")[-12000:]
            except Exception as exc: content = self.t("Could not read log file: {error}", error=exc)
        body = self.t("Bug report email body", app=config.APP_NAME, version=config.APP_VERSION, os=platform.platform(), python=sys.version.split()[0], language=self.translator.current_language, theme=self.theme, workers=self.workers_spin.value(), file_count=len(self.all_records), duplicate_groups=summarize(self.all_records)["duplicate_group_count"], duplicate_files=summarize(self.all_records)["duplicate_file_count"], log_path=str(log_path or ""), log_content=content)
        url = f"mailto:{config.AUTHOR_EMAIL}?subject={urllib.parse.quote(self.t('HashSieve bug report / feature request'))}&body={urllib.parse.quote(body)}"
        webbrowser.open(url)
        self._set_status("Bug report draft opened. Log file: {path}", path=str(log_path or ""))

    def about(self) -> None:
        QMessageBox.information(self, self.t("About"), f"{config.APP_NAME} {config.APP_VERSION}\n{self.t('A local-first Windows desktop tool for calculating file hashes and safely cleaning duplicate files.')}\n\n{self.t('Author')}: {config.AUTHOR_NAME}\n{self.t('Email')}: {config.AUTHOR_EMAIL}\n{config.LICENSE_NAME}")

    def _check_updates(self, manual: bool) -> None:
        if self.update_worker and self.update_worker.isRunning(): return
        self.update_worker = UpdateCheckWorker(manual, self); self.update_worker.result.connect(self._on_update_check_result); self.update_worker.start()

    def _on_update_check_result(self, has_update: bool, version: str, error: str, manual: bool) -> None:
        if has_update:
            if QMessageBox.information(self, self.t("Check for Updates"), self.t("A newer version of HashSieve is available: {version}. Open the GitHub repository now?", version=version), QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes: webbrowser.open(config.GITHUB_RELEASES_URL)
        elif manual:
            QMessageBox.information(self, self.t("No Updates"), self.t("You are using the latest version.", fallback="You are using the latest version."))

    # layout -------------------------------------------------------------
    def _save_table_layout(self) -> None:
        if not hasattr(self, "table"): return
        header = self.table.horizontalHeader()
        order = [COLUMNS[header.logicalIndex(v)][0] for v in range(header.count())]
        widths = {key: self.table.columnWidth(idx) for idx, (key, _) in enumerate(COLUMNS)}
        self.settings.set_many({"column_order": order, "column_widths": widths})

    def _restore_builtin_table_layout(self) -> None:
        """Restore the Python-defined column order and widths immediately."""
        header = self.table.horizontalHeader()
        header.blockSignals(True)
        try:
            for target_visual, (key, _label) in enumerate(COLUMNS):
                logical = COL_INDEX[key]
                current_visual = header.visualIndex(logical)
                if current_visual >= 0 and current_visual != target_visual:
                    header.moveSection(current_visual, target_visual)
            for key, width in DEFAULT_COLUMN_WIDTHS.items():
                self.table.setColumnWidth(COL_INDEX[key], width)
        finally:
            header.blockSignals(False)

    def _restore_table_layout(self) -> None:
        widths = self.settings.get("column_widths", {}) or {}
        order = self.settings.get("column_order", []) or []
        header = self.table.horizontalHeader()
        header.blockSignals(True)
        try:
            for key, width in widths.items():
                if key in COL_INDEX:
                    try:
                        self.table.setColumnWidth(COL_INDEX[key], min(2000, max(40, int(width))))
                    except (TypeError, ValueError):
                        pass
            seen: set[str] = set()
            valid_order: list[str] = []
            for key in order:
                if key in COL_INDEX and key not in seen:
                    seen.add(key)
                    valid_order.append(key)
            for target_visual, key in enumerate(valid_order):
                logical = COL_INDEX[key]
                current_visual = header.visualIndex(logical)
                if current_visual >= 0 and current_visual != target_visual:
                    header.moveSection(current_visual, target_visual)
        finally:
            header.blockSignals(False)

    def _restore_window_geometry(self) -> None:
        self.resize(int(self.settings.get("window_width", 1320)), int(self.settings.get("window_height", 820)))

    def closeEvent(self, event) -> None:
        if self._processing:
            if QMessageBox.question(self, self.t("Hashing is running"), self.t("Scanning/hashing is still running. Exit anyway?")) != QMessageBox.Yes: event.ignore(); return
            if self.worker: self.worker.cancel(); self.worker.wait(2000)
        self.settings.set_many({"window_width": self.width(), "window_height": self.height(), "keep_strategy": self.keep_strategy_combo.currentData() or "first", "follow_symlinks": self.follow_symlinks_checkbox.isChecked(), "include_hidden": self.include_hidden_checkbox.isChecked(), "ignore_empty_grouping": self.ignore_empty_checkbox.isChecked(), "use_recycle_bin": self.recycle_checkbox.isChecked(), "workers": self.workers_spin.value(), "show_duplicates_only": self.show_duplicates_only_checkbox.isChecked()})
        self._save_table_layout(); event.accept()
