# HashSieve v2.2026.07.19 validation report

This document records the release-source checks for HashSieve v2.2026.07.19.

## Automated checks

Run from the project root:

```powershell
python tools\check_locales.py
python tools\self_test.py
```

The automated suite validates:

- Python source parsing/compilation.
- JSON parsing for all locale and version files.
- Required UI translation keys across all 13 language packs.
- Placeholder consistency such as `{count}`, `{size}`, `{path}`, and `{version}`.
- Version consistency across `app/config.py`, `VERSION.json`, `version_info.txt`, and tests.
- Numeric comparison of newer, equal, and older version strings.
- Worker defaults and clamping to `1…logical CPU count`.
- Preference schema reset, settings persistence, corrupt-JSON recovery, and immutable defaults.
- Recursive scanning of nested folders.
- Equivalent/repeated input-path suppression.
- Hidden-file exclusion and inclusion.
- Symbolic-link cycle protection when link creation is supported.
- MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512 against Python reference implementations.
- Exact duplicate grouping by size plus all six hashes.
- Same-size but different-content files remaining separate.
- 0-byte files excluded from duplicate groups by default and grouped only when protection is disabled.
- Duplicate-group counts, duplicate-file counts, and reclaimable-space calculations.
- Keep-one selection behavior.
- UTF-8 BOM CSV output and six hash columns.
- Permanent-delete helper behavior on temporary test files.
- Ten distinct group backgrounds and group 11 → group 1 cycling.
- Neutral zebra backgrounds for ungrouped rows in both themes.
- Unified selection colors that do not overlap the ten group colors.
- Preservation of original row colors for deselection.
- Worker spin-button theme assets and stylesheet generation.
- Static GUI contracts for worker limits, focus release, localized status refresh, full-row painting, one-dialog default reset, and one-record-reference-per-row population.
- Synthetic 2,000-file stress pipeline with 20 duplicate groups and 200 duplicate files.

Expected success output:

```text
OK: 95 required UI keys and their placeholders are valid in every locale file.
OK: HashSieve core, settings, metadata, palette, and source-contract tests passed.
```

## Windows manual release checks

The following items depend on Windows GUI behavior and should be checked on the final source and final EXE:

### Launch and environment

- Launch from a normal, non-Administrator terminal.
- Confirm `python main.py` starts in a clean PySide6 environment.
- Confirm `run_conda_env.bat` creates/reuses `hashsieve-gui` and starts the app.
- Confirm the final one-file EXE starts on a clean Windows user account.
- Confirm the taskbar, title-bar, and EXE icons use the HashSieve logo.

### Input and processing

- Drag one file, multiple files, one folder, multiple folders, and a mixed selection.
- Confirm folders are scanned recursively.
- Confirm input is rejected/locked while processing is active.
- Confirm Stop cancels processing and clears the active progress state.
- Test a large folder and verify the GUI remains responsive.
- Confirm file and byte progress, files/s, and bytes/s update.

### Worker control

- Confirm the minimum is 1 and the maximum equals the machine's logical CPU count.
- Type a value below 1 and above the maximum; confirm it is clamped.
- Click the up/down buttons repeatedly; confirm they are visible in both themes.
- Confirm text highlighting and focus clear shortly after the final edit.
- Restart the app and confirm the saved valid worker value is restored.

### Table colors and selection

- Scan at least 11 duplicate groups and several unique files.
- Confirm groups 1–10 use ten visibly distinct full-row backgrounds.
- Confirm group 11 repeats group 1.
- Confirm unique files alternate neutral white/gray rows in light mode and two neutral dark shades in dark mode.
- Select rows from multiple groups; confirm all selected rows use one theme-specific selection color.
- Deselect rows; confirm each row immediately restores its original group or zebra background.

### Table interaction

- Sort multiple columns and confirm ascending/descending indicators move to the active column.
- Resize and reorder columns, restart, and confirm the layout persists.
- Use `Ctrl+A` and `Ctrl+C`; paste into a spreadsheet and confirm every selected row is copied as TSV.
- Use individual hash-copy actions and confirm all selected hash values are copied.
- Double-click a file and confirm Explorer opens its containing folder and selects the exact file.

### Language and theme

- Cycle through all 13 languages.
- Confirm menus, statistics, controls, status text, dialogs, and support actions update.
- Change language while a non-default status message is displayed; confirm the status text retranslates.
- Confirm light/dark theme colors, scrollbars, worker controls, table colors, and selected rows are readable.

### Defaults and persistence

- Change language, theme, workers, filters, keep strategy, sorting, column order, widths, and window size.
- Restart and confirm compatible settings persist.
- Choose Restore Defaults once; confirm one confirmation dialog only.
- Confirm all interface settings return to Python-defined defaults immediately.

### Export and deletion

- Export CSV and open it in Excel; confirm readable Unicode text and all expected columns.
- Test Remove Selected from List and confirm files remain on disk.
- Move temporary test files to the Recycle Bin.
- Test permanent deletion only with disposable files and verify the warning/confirmation.
- Confirm failed operations are recorded in the session log.

### Update, logs, and release assets

- Use Help → Check for Updates and confirm a visible current/update result.
- Confirm automatic startup checking remains silent when current or offline.
- Confirm one session log is reused until the application exits.
- Build with `build_windows.bat`.
- Confirm the build produces:

```text
release\HashSieve.exe
release\HashSieve.exe.sha256
release\HashSieve.exe.sha512
release\CHECKSUMS.txt
```

- Recalculate SHA-256 and SHA-512 and confirm they match the final uploaded assets.
