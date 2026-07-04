# HashSieve

**Version:** v1.2026.07.04

HashSieve is a local-first Windows desktop tool for recursively scanning files and folders, calculating multiple hash values, grouping exact duplicate files, exporting CSV reports, and safely cleaning duplicate copies after user review.

Users can drag one or more files, one or more folders, or a mixed set of files and folders into the app. Folders are scanned recursively, so subfolders and deeper nested folders are included. After files are added, hash calculation starts automatically. Files are grouped as duplicates only when **file size + MD5 + SHA-1 + CRC32 + SHA-256 + SHA-384 + SHA-512** are all identical.

HashSieve is an independent project. It is not affiliated with NirSoft HashMyFiles or any other third-party tool. Product names are mentioned only to describe comparable workflows.

![HashSieve logo](assets/hashsieve_logo.png)

## Logo concept

The HashSieve logo combines a sieve/funnel with the hash symbol `#`. The sieve represents filtering a large collection of files, the `#` represents hash values, and the filtered dots represent duplicate copies being separated from files you keep. The blue-to-green palette is intended to feel technical, safe, and cleanup-oriented.

## Main features

- Drag-and-drop files and folders from Windows File Explorer.
- Add multiple files and folders from buttons or the File menu.
- Automatic hash calculation after files/folders are added.
- Recursive folder scanning, including subfolders and deeper nested folders.
- Hidden/system files are excluded by default and can be enabled in Settings when needed.
- Path de-duplication when parent and child folders are both added.
- Multi-hash calculation in one scan: MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512.
- Duplicate grouping by file size plus all six hash values.
- Optional setting to keep 0-byte empty files out of duplicate groups. Empty files are still listed and hashed.
- Worker thread default: total logical CPU cores minus 2, with a minimum of 1.
- Scanning and hashing progress with file count, total size, files/second, and bytes/second.
- Non-blocking large-folder pipeline: scan in a background thread, hash through bounded worker threads, then build the result table once.
- Drag-and-drop and add/delete/export actions are locked while scanning or hashing is running.
- Restore Defaults option in both Tools and Settings.
- HashMyFiles-like table with filename, size, hashes, extension, timestamps, hash duration, full path, and errors.
- Group-column sorting keeps duplicate groups above ungrouped files.
- The active sort column shows an ▲ or ▼ indicator in the column header.
- Double-click a row to open the file location and select the file in Windows Explorer.
- Double-click a column separator to auto-fit that column width to visible content.
- Drag a column separator to resize a single column.
- Drag a column header to reorder columns; column order, widths, and sort state are saved.
- Higher-contrast scrollbars are used in both light and dark themes.
- Ctrl/Shift multi-selection in the table.
- Right-click and Edit-menu actions for copying all six hash types, copying paths, copying rows, opening file location, removing rows from the list, and deleting selected files.
- Duplicate cleanup workflow:
  - `Select duplicates except one` keeps one file in each duplicate group,
  - automatically selects the other duplicate copies,
  - users can Ctrl-click to adjust the selection,
  - `Delete Selected` deletes only selected rows.
- Recycle Bin deletion by default through `send2trash`.
- Optional permanent-delete mode with an extra `DELETE` confirmation.
- Export all rows to CSV with UTF-8 BOM for Excel compatibility.
- Search/filter box and `Duplicates only` view.
- Multi-language UI with bundled language packs and native-language names in the Settings dialog.
- Light and dark themes, including dark Settings dialog styling.
- Automatic silent startup update check against the GitHub `VERSION.json`. A notification appears only when a newer version is available; no notice is shown when the current version is latest or the connection fails.
- Manual `Check for Updates` shows a confirmation dialog even when no update is available or the update check cannot be completed.
- One log file per application session. Bug-report email drafts include the current log content and the log-file path.
- PyInstaller one-file EXE build script with SHA-256 and SHA-512 checksum output.

## Supported languages

Bundled UI language packs:

- English
- 繁體中文
- 简体中文
- 日本語
- 한국어
- Español
- Français
- Deutsch
- Português (Brasil)
- Русский
- ไทย
- Bahasa Indonesia
- العربية

The language files include all UI keys used by this version. Native-speaker corrections and improvements are welcome.

## Quick start from source

### Option A: use the launcher

On Windows, double-click:

```bat
run_conda.bat
```

The launcher creates a project-local `.venv`, installs dependencies, and starts the app.

### Option B: manual setup

```bat
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install --prefer-binary -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Building the EXE

Open PowerShell in the project folder and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build_onefile_exe.ps1
```

The final executable and checksum files will be generated at:

```text
release\HashSieve.exe
release\HashSieve.exe.sha256
release\HashSieve.exe.sha512
release\CHECKSUMS.txt
```

After a successful build, the script deletes intermediate build folders such as `build`, `dist`, `.build_venv`, and `__pycache__`.

## Release assets and checksums

For GitHub Releases, upload these files from the local `release` folder as release assets:

```text
HashSieve.exe
HashSieve.exe.sha256
HashSieve.exe.sha512
CHECKSUMS.txt
```

`CHECKSUMS.txt` is meant to be attached to the GitHub Release together with `HashSieve.exe`, not committed into the repository as a changing build artifact. You may also paste the checksum values into the release notes so users can verify the downloaded EXE.

Example checksum format:

```text
SHA256  <sha256>  HashSieve.exe
SHA512  <sha512>  HashSieve.exe
```

## Recommended workflow

1. Open `HashSieve.exe` or run `run_conda.bat` from source.
2. Drag files/folders into the app, or click `Add Files` / `Add Folder`.
3. Wait for automatic scanning and hash calculation to finish.
4. Review duplicate groups.
5. Click `Select duplicates except one`.
6. Review the selected rows. Ctrl-click to add or remove files from the selection.
7. Click `Delete Selected`.
8. Export a CSV report if you want a record of the scan.

Deletion is intentionally not fully automatic. HashSieve selects duplicate copies first so the user can review before changing files on disk.

## What does `follow_symlinks` mean?

A symbolic link, or symlink, is a filesystem entry that points to another file or folder. When `follow_symlinks` is off, recursive scanning does not follow those links. When it is on, the scanner may enter the linked target as if it were a real folder.

The default is **off** because symlinks can point outside the folder you dragged in, or in unusual cases they can create scan loops.

## Empty-file duplicate grouping

The default setting ignores 0-byte empty files when creating duplicate groups. Empty files are still listed and hashed, but they are not grouped as duplicates. This avoids accidentally deleting intentional placeholder files such as `__init__.py`.

## Logs and settings

- Settings: `%APPDATA%\HashSieve\settings.json`
- Logs: `%LOCALAPPDATA%\HashSieve\Logs`

HashSieve creates one log file per app session. Bug-report emails paste the current log content into the email body and also show the log-file path so the user can attach it.

## Preference compatibility policy

HashSieve stores a `preferences_schema_version` inside `settings.json`. The schema version is changed only when old settings are not compatible with the current defaults or when a safety-related default should be reset. If the schema changes, HashSieve resets settings to the current defaults instead of accumulating many one-off migration branches. If the schema is unchanged, HashSieve keeps known settings, merges new optional keys, and ignores unknown keys.

## Version policy

All pre-GitHub fixes and feature refinements for the first public release are consolidated under **v1.2026.07.04**. This version number is intentionally kept stable until the first GitHub publication.

## GitHub release checklist

1. Commit and push the source code to `main`.
2. Build the EXE with `build_onefile_exe.ps1`.
3. Confirm the `release` folder contains `HashSieve.exe`, checksum files, and `CHECKSUMS.txt`.
4. Create a GitHub Release with tag `v1.2026.07.04` and target `main`.
5. Use release title `HashSieve v1.2026.07.04`.
6. Paste the release notes from `RELEASE_NOTES_v1.2026.07.04.md`.
7. Attach `HashSieve.exe`, `HashSieve.exe.sha256`, `HashSieve.exe.sha512`, and `CHECKSUMS.txt`.
8. Mark it as the latest release and publish.

## Author and support

Author: Shih-Han Wang  
Email: wangsh@vt.edu

Bug reports, feature requests, GitHub stars, and sponsorship are all appreciated.

## Links

- GitHub repository: https://github.com/dogs1231992/HashSieve
- GitHub Releases: https://github.com/dogs1231992/HashSieve/releases
- GitHub Sponsors: https://github.com/sponsors/dogs1231992
- Buy Me a Coffee: https://buymeacoffee.com/dogs1231992
- Author / bug reports: wangsh@vt.edu

---

## License

HashSieve is released under the [MIT License](LICENSE).
