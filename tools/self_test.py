# -*- coding: utf-8 -*-
"""HashSieve pre-release self-test.

This test intentionally avoids importing PySide6 so it can validate the core and
release metadata even on a build machine without a GUI display.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import tempfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import config
from app.core.csv_exporter import export_to_csv
from app.core.duplicate_finder import annotate_groups, choose_files_to_delete, summarize
from app.core.file_ops import delete_files
from app.core.hasher import compute_all_hashes
from app.core.scanner import scan_paths
from app.i18n.translator import Translator
from app.ui import styles
from app.utils.app_settings import (
    AppSettings,
    PREFERENCES_SCHEMA_VERSION,
    clamp_worker_count,
    default_worker_count,
    max_worker_count,
    new_default_settings,
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def test_version_metadata() -> None:
    version_data = json.loads((ROOT / "VERSION.json").read_text(encoding="utf-8"))
    version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")
    check(config.APP_VERSION == "v2.2026.07.19", "config version mismatch")
    check(version_data["version"] == config.APP_VERSION, "VERSION.json mismatch")
    check(config.APP_VERSION in version_info, "version_info.txt mismatch")
    check(config.is_newer_version("v2.2026.07.20"), "newer version not detected")
    check(not config.is_newer_version("v2.2026.07.19"), "same version treated as newer")
    check(not config.is_newer_version("v1.2026.07.04"), "older version treated as newer")


def test_workers_and_settings(tmp: Path) -> None:
    maximum = max_worker_count()
    check(maximum >= 1, "invalid max worker count")
    check(1 <= default_worker_count() <= maximum, "invalid default worker count")
    check(clamp_worker_count(0) == 1, "worker lower clamp failed")
    check(clamp_worker_count(maximum + 100) == maximum, "worker upper clamp failed")

    config_path = tmp / "settings.json"
    config_path.write_text(
        json.dumps(
            {
                "preferences_schema_version": PREFERENCES_SCHEMA_VERSION,
                "language": "th-TH",
                "workers": maximum + 100,
            }
        ),
        encoding="utf-8",
    )
    settings = AppSettings(config_path)
    check(settings.get("workers") == maximum, "saved worker count was not clamped")
    settings.set("workers", -20)
    check(settings.get("workers") == 1, "settings writer lower clamp failed")

    # Mutable preferences must never mutate the Python defaults or internal
    # state through shared list/dict references.
    defaults_a = new_default_settings()
    defaults_a["column_order"].append("filename")
    check(new_default_settings()["column_order"] == [], "default settings are not isolated")
    settings.set("column_order", ["filename", "size"])
    snapshot = settings.as_dict()
    snapshot["column_order"].append("md5")
    check(settings.get("column_order") == ["filename", "size"], "settings snapshot leaked mutable state")
    settings.reset_defaults()
    check(settings.get("column_order") == [], "reset defaults did not restore built-in column order")
    check(settings.get("column_widths") == {}, "reset defaults did not restore built-in column widths")

    old_path = tmp / "old_settings.json"
    old_path.write_text(json.dumps({"preferences_schema_version": 1, "language": "zh-TW"}), encoding="utf-8")
    migrated = AppSettings(old_path)
    check(migrated.get("language") == "en-US", "schema reset did not apply English default")

    corrupt_path = tmp / "corrupt_settings.json"
    corrupt_path.write_text("{not valid JSON", encoding="utf-8")
    recovered = AppSettings(corrupt_path)
    check(recovered.get("language") == "en-US", "corrupt settings did not recover to defaults")
    check(json.loads(corrupt_path.read_text(encoding="utf-8"))["preferences_schema_version"] == PREFERENCES_SCHEMA_VERSION, "corrupt settings file was not repaired")


def test_scan_hash_group_csv(tmp: Path) -> None:
    root = tmp / "scan"
    nested = root / "nested"
    nested.mkdir(parents=True)
    payload = b"HashSieve duplicate payload\n" * 4096
    (root / "same-a.bin").write_bytes(payload)
    (nested / "same-b.bin").write_bytes(payload)
    (nested / "unique.bin").write_bytes(payload + b"unique")
    (nested / "same-size-different.bin").write_bytes(b"X" * len(payload))
    (root / "empty-a.py").write_bytes(b"")
    (nested / "empty-b.py").write_bytes(b"")
    (root / ".hidden.bin").write_bytes(b"hidden")

    scanned, errors = scan_paths([root, root / "same-a.bin"], include_hidden=False)
    check(not errors, f"scan errors: {errors}")
    names = {item.path.name for item in scanned}
    check(".hidden.bin" not in names, "hidden file included by default")
    check(len(scanned) == 6, "recursive scan/dedup count mismatch")

    scanned_hidden, _ = scan_paths([root], include_hidden=True)
    check(any(item.path.name == ".hidden.bin" for item in scanned_hidden), "hidden file option failed")

    # Following symbolic links must not loop forever when a link points to an
    # ancestor. Skip this check on platforms/filesystems that forbid symlinks.
    cycle_link = nested / "cycle-to-root"
    try:
        cycle_link.symlink_to(root, target_is_directory=True)
    except (OSError, NotImplementedError):
        cycle_link = None
    if cycle_link is not None:
        scanned_cycle, cycle_errors = scan_paths([root], include_hidden=False, follow_symlinks=True)
        check(not cycle_errors, f"symlink-cycle scan errors: {cycle_errors}")
        check(len(scanned_cycle) == len(scanned), "symlink cycle caused duplicate or recursive scanning")

    records = [compute_all_hashes(item.path) for item in scanned]
    check(all(not record.error for record in records), "hashing produced errors")
    check(all(len(record.hashes) == 6 for record in records), "not all six hashes were calculated")

    a = next(record for record in records if record.filename == "same-a.bin")
    check(a.hashes["md5"] == hashlib.md5(payload).hexdigest(), "MD5 mismatch")
    check(a.hashes["sha1"] == hashlib.sha1(payload).hexdigest(), "SHA-1 mismatch")
    check(a.hashes["sha256"] == hashlib.sha256(payload).hexdigest(), "SHA-256 mismatch")
    check(a.hashes["sha384"] == hashlib.sha384(payload).hexdigest(), "SHA-384 mismatch")
    check(a.hashes["sha512"] == hashlib.sha512(payload).hexdigest(), "SHA-512 mismatch")
    check(a.hashes["crc32"] == f"{zlib.crc32(payload) & 0xFFFFFFFF:08x}", "CRC32 mismatch")

    # Files with the same size but different content must not be grouped.
    same_size_different = next(record for record in records if record.filename == "same-size-different.bin")
    check(same_size_different.size == a.size, "same-size test fixture is invalid")
    check(same_size_different.duplicate_key() != a.duplicate_key(), "six-hash duplicate key did not distinguish content")

    annotate_groups(records, ignore_empty_grouping=True)
    duplicate_groups = {record.group_id for record in records if record.is_duplicate}
    check(len(duplicate_groups) == 1, "expected one non-empty duplicate group")
    check(sum(record.is_duplicate for record in records) == 2, "duplicate file count mismatch")
    check(not any(record.is_duplicate for record in records if record.size == 0), "0-byte files were grouped")

    summary = summarize(records)
    check(summary["duplicate_group_count"] == 1, "summary group count mismatch")
    check(summary["duplicate_file_count"] == 2, "summary duplicate count mismatch")
    check(summary["reclaimable_space"] == len(payload), "reclaimable size mismatch")
    check(len(choose_files_to_delete(records, "first")) == 1, "keep-one selection mismatch")

    annotate_groups(records, ignore_empty_grouping=False)
    check(sum(record.is_duplicate for record in records if record.size == 0) == 2, "empty grouping option failed")

    output = tmp / "export.csv"
    count = export_to_csv(records, output)
    check(count == len(records), "CSV row count return mismatch")
    raw = output.read_bytes()
    check(raw.startswith(b"\xef\xbb\xbf"), "CSV is missing UTF-8 BOM")
    with output.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check(len(rows) == len(records), "CSV data row count mismatch")
    check({"MD5", "SHA-1", "CRC32", "SHA-256", "SHA-384", "SHA-512"}.issubset(set(rows[0].keys())), "CSV hash columns missing")

    disposable = tmp / "delete-me.tmp"
    disposable.write_text("temporary", encoding="utf-8")
    deleted, failed = delete_files([str(disposable)], use_recycle_bin=False)
    check(deleted == [str(disposable)] and not failed and not disposable.exists(), "permanent delete helper failed")



def test_stress_pipeline(tmp: Path) -> None:
    """Exercise the core pipeline with thousands of files without touching user data."""
    root = tmp / "stress"
    root.mkdir()
    expected_groups = 20
    copies_per_group = 10
    for group in range(expected_groups):
        payload = (f"duplicate-group-{group:02d}\n" * 4).encode("utf-8")
        for copy_index in range(copies_per_group):
            (root / f"dup_{group:02d}_{copy_index:02d}.bin").write_bytes(payload)
    unique_count = 1800
    for index in range(unique_count):
        (root / f"unique_{index:04d}.bin").write_bytes(f"unique-payload-{index:04d}".encode("utf-8"))

    scanned, errors = scan_paths([root])
    check(not errors, f"stress scan errors: {errors[:3]}")
    check(len(scanned) == expected_groups * copies_per_group + unique_count, "stress scan count mismatch")
    records = [compute_all_hashes(item.path) for item in scanned]
    annotate_groups(records, ignore_empty_grouping=True)
    summary = summarize(records)
    check(summary["duplicate_group_count"] == expected_groups, "stress duplicate group mismatch")
    check(summary["duplicate_file_count"] == expected_groups * copies_per_group, "stress duplicate file mismatch")
    check(len(choose_files_to_delete(records, "first")) == expected_groups * (copies_per_group - 1), "stress keep-one selection mismatch")

def test_locales() -> None:
    translator = Translator(ROOT / "app" / "i18n" / "locales", "en-US")
    languages = translator.available_languages()
    check(len(languages) == 13, "expected 13 bundled languages")
    for language in languages:
        translator.set_language(language)
        check(translator.t("Files") != "", f"empty Files translation for {language}")
        check(translator.t("Duplicate groups") != "", f"empty duplicate-group translation for {language}")


def test_palette_and_source_contract() -> None:
    check(len(styles._GROUP_PALETTE_LIGHT) == 10, "light group palette must contain 10 colors")
    check(len(styles._GROUP_PALETTE_DARK) == 10, "dark group palette must contain 10 colors")
    check(styles.get_group_color("light", 1) == styles.get_group_color("light", 11), "group color cycle failed")
    check(styles.get_group_color("dark", 10) != styles.get_group_color("dark", 1), "group colors are not distinct")
    light_group_colors = [styles.get_group_color("light", index) for index in range(1, 11)]
    dark_group_colors = [styles.get_group_color("dark", index) for index in range(1, 11)]
    check(len({background for background, _foreground in light_group_colors}) == 10, "light group backgrounds are not unique")
    check(len({background for background, _foreground in dark_group_colors}) == 10, "dark group backgrounds are not unique")
    check(len({foreground for _background, foreground in light_group_colors}) == 1, "light group text should remain neutral")
    check(len({foreground for _background, foreground in dark_group_colors}) == 1, "dark group text should remain neutral")
    check(styles.get_ungrouped_row_color("light", 0) != styles.get_ungrouped_row_color("light", 1), "ungrouped light alternation failed")
    check(styles.get_ungrouped_row_color("dark", 0) != styles.get_ungrouped_row_color("dark", 1), "ungrouped dark alternation failed")

    for name in ("spin_up_light.svg", "spin_down_light.svg", "spin_up_dark.svg", "spin_down_dark.svg"):
        check((ROOT / "assets" / name).is_file(), f"missing spin-button asset: {name}")
    light_css = styles.build_stylesheet("light", ROOT / "assets")
    dark_css = styles.build_stylesheet("dark", ROOT / "assets")
    check("spin_up_light.svg" in light_css and "spin_down_light.svg" in light_css, "light spin arrows are not bundled into QSS")
    check("spin_up_dark.svg" in dark_css and "spin_down_dark.svg" in dark_css, "dark spin arrows are not bundled into QSS")
    check("background-color: #D6E0DE" in light_css, "light spin-button contrast color missing")
    check("background-color: #3B4D49" in dark_css, "dark spin-button contrast color missing")
    check("$SPIN_" not in light_css and "$SPIN_" not in dark_css, "unresolved spin icon placeholder")

    source = (ROOT / "app" / "ui" / "main_window.py").read_text(encoding="utf-8")
    check("setRange(1, max_worker_count())" in source, "GUI worker maximum is not enforced")
    check("get_ungrouped_row_color" in source, "ungrouped row colors are not applied")
    check("for col in range(t.columnCount())" in source, "full-row group coloring is not applied")
    check("RowColorDelegate" in source and "ROW_BACKGROUND_ROLE" in source, "explicit row-background delegate is missing")
    delegate_source = (ROOT / "app" / "ui" / "widgets.py").read_text(encoding="utf-8")
    check('tokens["table_selection_bg"]' in delegate_source, "unified selection background is missing")
    check('tokens["table_selection_text"]' in delegate_source, "selection text color is missing")
    check("stored_background" in delegate_source and "stored_foreground" in delegate_source, "original row colors are not retained for deselection")
    check("opt.state &= ~QStyle.State_Selected" in delegate_source, "Qt selection background is not suppressed")
    check("if selected:" in delegate_source, "selection-specific painting is missing")
    check(styles.LIGHT_TOKENS["table_selection_bg"] not in {bg for bg, _ in light_group_colors}, "light selection color overlaps a group background")
    check(styles.DARK_TOKENS["table_selection_bg"] not in {bg for bg, _ in dark_group_colors}, "dark selection color overlaps a group background")
    check(styles.LIGHT_TOKENS["table_selection_text"] == "#FFFFFF", "light selection text contrast is unexpected")
    check(styles.DARK_TOKENS["table_selection_text"] == "#FFFFFF", "dark selection text contrast is unexpected")
    check("self._refresh_status()" in source, "language-sensitive status refresh is missing")
    check("worker_focus_release_timer" in source and "line_edit.deselect()" in source, "worker focus-release behavior is missing")
    check("build_stylesheet(self.theme, get_assets_dir())" in source, "theme stylesheet does not receive packaged assets")
    check("self.settings.as_dict()" in source, "Restore Defaults is not based on the settings snapshot")
    restore_segment = source[source.index("    def restore_defaults"):source.index("    def open_log_folder")]
    check("QMessageBox.information" not in restore_segment, "Restore Defaults still shows a second completion dialog")
    check("_restore_builtin_table_layout" in source, "Restore Defaults does not reset table layout immediately")
    check(source.count("rec=rec") == 1, "FileRecord is redundantly stored in every table cell")
    check("table.setUpdatesEnabled(True)" in source and "table.viewport().update()" in source, "table refresh cleanup is incomplete")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="HashSieve_self_test_") as temp_dir:
        tmp = Path(temp_dir)
        test_version_metadata()
        test_workers_and_settings(tmp)
        test_scan_hash_group_csv(tmp)
        test_stress_pipeline(tmp)
        test_locales()
        test_palette_and_source_contract()
    print("OK: HashSieve core, settings, metadata, palette, and source-contract tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
