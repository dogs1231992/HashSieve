# Changelog

## v1.2026.07.04 - 2026-07-04

First public release. All internal pre-GitHub iterations are consolidated into this single version number.

### Added

- Standalone HashSieve application for recursive hash calculation and exact duplicate-file cleanup.
- Drag-and-drop support for files, folders, and mixed file/folder input.
- Automatic hash calculation after files/folders are added.
- Recursive folder scanning with hidden/system files excluded by default, optional hidden-file inclusion, and optional symbolic-link following.
- Multi-hash calculation: MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512.
- Duplicate grouping rule based on file size plus all six hash values.
- Default option to exclude 0-byte empty files from duplicate groups while still listing and hashing them.
- Worker default set to logical CPU cores minus 2, with a minimum of 1.
- Non-blocking large-folder pipeline: background scanning, bounded worker-thread hashing, and one final result-table build.
- Scan/hash progress reporting with file count, total size, files/second, and bytes/second.
- Stop handling that resets the progress bar and status correctly.
- Result table with filename, size, hashes, extension, timestamps, hash duration, full path, and errors.
- Search/filter and duplicate-only view.
- Group sorting behavior that keeps grouped duplicate rows above ungrouped rows.
- Sort-direction indicators in table column headers using ▲ for ascending and ▼ for descending.
- Ctrl/Shift multi-selection.
- `Select duplicates except one` workflow that selects duplicate copies while keeping one file per group.
- Recycle Bin deletion through `send2trash` and optional permanent deletion with `DELETE` confirmation.
- CSV export with UTF-8 BOM for Excel compatibility.
- Double-click row behavior that opens Windows Explorer at the file location and selects the file.
- Column auto-fit by double-clicking separators, manual column resizing, column reordering, and saved column layout/sort state.
- Complete Edit-menu and right-click menu coverage for copy hash, copy path, copy row, open file location, remove row, and delete selected.
- Settings dialog with native-language names, Restore Defaults, dark-theme styling, and automatic focus clearing after language/theme selection.
- Bundled UI localization files for English, Traditional Chinese, Simplified Chinese, Japanese, Korean, Spanish, French, German, Portuguese (Brazil), Russian, Thai, Indonesian, and Arabic.
- Sponsor labels with clear local-language prefixes such as `Sponsor:` / `贊助：` / `赞助：`.
- HashSieve logo assets in PNG, SVG, and ICO formats.
- Runtime Tk window icon, not only the EXE file icon.
- One session log file per application run.
- Bug-report email draft that includes the current log content and log-file path instead of creating a separate bug-report text file.
- Automatic silent startup update check against GitHub `VERSION.json`; users are notified only when a newer version is available.
- Manual update check confirmation when no update is available or the version check cannot be completed.
- Versioned preference schema handling through `preferences_schema_version`.
- PyInstaller one-file build script, Windows version resource, release checksums, and build-folder cleanup.
- GitHub release notes template for v1.2026.07.04.

### Changed

- Renamed the project to HashSieve.
- Replaced the old mark/delete-marked workflow with selection-based deletion.
- Renamed `Clear` to `Clear List` to avoid confusion with deleting files.
- Improved localization coverage so runtime UI keys are present in every bundled language file.
- Improved Traditional Chinese and Simplified Chinese wording consistency.
- Improved non-English wording for recursive scanning, symbolic-link options, update checking, and recycle-bin errors.
- Improved light/dark scrollbar contrast so the scrollbar thumb is easier to see.
- Updated README, VERSION.json, version_info.txt, PyInstaller spec, build script, locale documentation, and release notes for v1.2026.07.04.

### Fixed

- Fixed GUI freezing caused by scanning folders on the main Tkinter thread.
- Fixed heavy result-table rebuilds during hashing by building the table once after hashing finishes.
- Fixed high memory/overhead behavior from submitting one future per file by using bounded worker threads.
- Fixed drag-and-drop/add actions remaining active while scanning or hashing.
- Fixed Explorer `/select` handling for paths with spaces and files without extensions.
- Fixed progress/status text remaining stuck after result-table creation or after Stop.
- Fixed English fallback labels appearing in non-English menus and dialogs.
- Fixed older preference files keeping hidden-file scanning enabled by resetting incompatible preference schemas to the current defaults.
- Fixed selection highlight remaining inside language/theme comboboxes after choosing an option.
- Fixed English sponsor items lacking a clear sponsor prefix by loading the en-US locale file as a real locale.
- Fixed source package cleanup by excluding `__pycache__` and compiled Python artifacts from the release-ready source archive.
