# Changelog

All notable changes to HashSieve are documented here.

## v2.2026.07.19 - 2026-07-19

### Overview

Version 2 is a major interface and usability update. HashSieve moved from Tkinter/ttk to PySide6/Qt 6 while retaining the established v1 core behavior: recursive scanning, one-pass calculation of six hashes, exact duplicate grouping by file size plus all hashes, 0-byte protection, CSV export, reviewed selection, and optional Recycle Bin deletion.

All pre-release v2 GUI work has been consolidated into this public version number.

### Added

- Modern PySide6/Qt 6 desktop interface.
- Card-based drag-and-drop area and statistics dashboard.
- Light and dark themes with independently styled input fields, spin buttons, scrollbars, table surfaces, and selection states.
- Ten repeating full-row background colors for duplicate groups.
- Neutral zebra backgrounds for files outside duplicate groups.
- One unified, high-contrast selected-row color per theme; deselection restores the original group or zebra background.
- Five keep-file strategies: first, oldest, newest, shortest path, and longest path.
- Native-language names for all language choices.
- Localized bottom status messages that immediately refresh after a language change.
- Manual update-check result messages in addition to the silent startup check.
- Isolated conda and virtual-environment launchers for reliable PySide6 execution.
- Isolated Windows build workflow with automatic SHA-256, SHA-512, and combined checksum generation.
- Bundled locale checker, core self-test, validation report, and release checklist.

### Changed

- Replaced the v1 Tkinter/ttk GUI with a modern PySide6/Qt 6 GUI.
- Changed the default language for new or reset settings to English.
- Limited worker count to `1…logical CPU count`; typed and saved out-of-range values are clamped automatically.
- Set the default worker count to logical CPU count minus 2, with a minimum of 1.
- Made the worker value save immediately and release keyboard focus shortly after editing.
- Displayed duplicate identity through full-row background colors instead of colored text.
- Made selected rows temporarily use a single theme-specific fill rather than hiding the user's selection behind group colors.
- Made ungrouped rows alternate between neutral colors in both themes.
- Preserved deterministic scan order after parallel hashing so the “first” keep strategy is repeatable.
- Made table columns movable, resizable, sortable, and persistent across launches.
- Changed `Ctrl+C` to copy every selected row as tab-separated data.
- Moved all commonly used preferences to the main surface and View menu; removed the redundant settings dialog entry.
- Made Restore Defaults reset the complete visible state from immutable Python-defined defaults after one confirmation.
- Kept automatic update checks silent when current/offline while making manual checks explicit.
- Updated application metadata, Windows file metadata, update metadata, documentation, tests, and release notes to `v2.2026.07.19`.

### Fixed

- Prevented the GUI from freezing while recursively scanning or hashing large file collections.
- Replaced unbounded per-file task submission with a bounded worker pipeline.
- Avoided rebuilding the complete result table during hash progress; results are populated after processing completes.
- Throttled scan and byte-progress messages to keep the GUI event queue responsive.
- Locked file/folder input while processing is active.
- Prevented worker values above the machine's logical CPU count or below 1.
- Corrected worker spin-button contrast and arrow visibility in light and dark themes.
- Restored automatic focus release after worker-count edits.
- Prevented Qt/Windows styles from overriding duplicate-group row backgrounds.
- Ensured group text uses a consistent neutral foreground rather than group-specific text colors.
- Ensured group 11 repeats group 1's background, group 12 repeats group 2, and so on.
- Ensured files outside duplicate groups use white/gray zebra rows in light mode and two neutral dark shades in dark mode.
- Ensured selected rows use one unified color and return to their original row color immediately after deselection.
- Corrected double-click/Open File Location handling so Windows Explorer opens the containing folder and selects the target file when possible.
- Prevented equivalent relative, absolute, case-normalized, or repeated input paths from creating duplicate rows.
- Prevented recursive symbolic-link cycles when link following is enabled.
- Corrected numeric version comparison so an older unequal version is not reported as an update.
- Repaired corrupt or truncated settings JSON by recreating clean defaults.
- Prevented mutable saved layout values from changing the built-in defaults in memory.
- Reset sorting, column order, column widths, window size, language, theme, filters, and surface options correctly during Restore Defaults.
- Removed the unnecessary second Restore Defaults completion dialog.
- Prevented repeated intermediate settings writes while restoring table layout.
- Reduced large-table memory use by storing each `FileRecord` reference once per row instead of once per cell.
- Guaranteed table updates are re-enabled after result population even if an exception occurs.
- Updated bottom selection status dynamically as rows are selected or deselected.
- Removed the redundant native status bar that duplicated information already shown in the dashboard.
- Corrected missing or stale translations in menus, controls, statistics, status messages, and support actions.
- Ensured one session log is reused for the entire application process.

### Core behavior retained from v1

- Mixed file/folder drag and drop.
- Recursive nested-folder scanning.
- MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512 in one pass.
- Exact duplicate rule: file size plus all six hashes must match.
- 0-byte files excluded from duplicate groups by default.
- Hidden files excluded by default.
- Symbolic links not followed by default.
- CSV export with UTF-8 BOM.
- Copy hashes, paths, and complete rows.
- Review-first selection before deletion.
- Recycle Bin deletion enabled by default.
- Session logging and GitHub update checks.

### Validation

- Python syntax/compilation checks for all source files.
- JSON parsing and required-key/placeholder checks across all 13 language packs.
- Version consistency across application, update, Windows resource, documentation, and test metadata.
- Recursive scan, normalized-path deduplication, hidden-file, and symbolic-link cycle tests.
- Reference validation for all six hash algorithms.
- Exact duplicate, same-size/different-content, 0-byte, keep-one, and reclaimable-space tests.
- UTF-8 BOM CSV and permanent-delete helper tests using temporary files.
- Worker limits, settings persistence, schema reset, corrupt-settings recovery, and immutable-default tests.
- Ten-color group palette, group-color cycling, neutral zebra, and unified selection-color source-contract tests.
- Synthetic 2,000-file stress test containing 20 duplicate groups.

## v1.2026.07.04 - 2026-07-04

### Initial public release

- Tkinter/ttk desktop interface with file and folder drag-and-drop.
- Recursive file and folder scanning.
- MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512 calculation.
- Exact duplicate grouping by file size plus all six hashes.
- 0-byte duplicate-group protection.
- Background scanning and hashing with progress reporting.
- Reviewed duplicate selection and Recycle Bin deletion.
- CSV export, multilingual UI, themes, session logging, update checking, and one-file Windows packaging.
