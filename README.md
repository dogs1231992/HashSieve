<p align="center">
  <img src="assets/hashsieve_logo.png" alt="HashSieve logo" width="128">
</p>

<h1 align="center">HashSieve</h1>

<p align="center">
  A local-first Windows hash calculator and exact duplicate-file cleaner.
</p>

<p align="center">
  <strong>Current release: v2.2026.07.19</strong><br>
  Windows desktop application · PySide6 / Qt 6 · MIT License
</p>

HashSieve recursively scans files and folders, calculates six hash values in one pass, groups exact duplicate files, exports detailed CSV reports, and lets the user review the selection before anything is deleted.

Version 2 is a major GUI modernization release. The original Tkinter interface has been replaced by a modern PySide6/Qt 6 interface, while the core scanning, hashing, duplicate-detection, CSV, and deletion behavior remains compatible with the v1 workflow.

## Exact duplicate rule

HashSieve considers two files identical only when **all seven values** match:

1. File size
2. MD5
3. SHA-1
4. CRC32
5. SHA-256
6. SHA-384
7. SHA-512

This intentionally favors certainty over speed. A matching filename, extension, size, or single hash is never enough by itself.

## Features

### Input and scanning

- Drag and drop one or more files, folders, or a mixed selection.
- Add files and folders through the interface.
- Recursively scan all nested subfolders.
- Automatically begin scanning and hashing after input is added.
- Deduplicate equivalent input paths so the same file is not listed twice.
- Exclude hidden files by default.
- Do not follow symbolic links by default.
- Prevent recursive symbolic-link loops when link following is enabled.
- Lock input and destructive controls while a scan or hash job is running.

### Hashing and progress

- Calculate MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512 in one file-reading pass.
- Run scanning and hashing outside the GUI thread.
- Use a bounded worker pipeline suitable for large file collections.
- Default workers: logical CPU count minus 2, with a minimum of 1.
- Enforce a worker range of 1 through the machine's reported logical CPU count.
- Display file-count progress, byte progress, files per second, and bytes per second.
- Preserve deterministic scan order after parallel hashing.

### Duplicate review and cleanup

- Group only files whose size and all six hashes match.
- List and hash 0-byte files, but exclude them from duplicate groups by default.
- Select every duplicate copy except one file in each group.
- Choose which file to keep by:
  - First file in scan order
  - Oldest modified file
  - Newest modified file
  - Shortest path
  - Longest path
- Adjust automatic selections with Ctrl-click or Shift-click before deletion.
- Move selected files to the Recycle Bin by default.
- Optionally use permanent deletion after explicit confirmation.
- Remove rows from the list without deleting the underlying files.

### Table and visual workflow

- Display filenames, size, six hashes, extension, timestamps, hash duration, full path, and errors.
- Use ten repeating full-row background colors for duplicate groups.
- Restart the group palette at group 11, group 21, and so on.
- Use neutral zebra rows for files outside duplicate groups.
- Use one high-contrast selection color per theme; deselecting restores the original group or zebra background.
- Search and filter the result table.
- Show duplicate files only.
- Sort any column with an ascending or descending indicator.
- Resize and reorder columns; preserve table layout between launches.
- Double-click a row to open its containing folder and select the file in Windows Explorer.

### Copy and export

- Copy MD5, SHA-1, CRC32, SHA-256, SHA-384, or SHA-512 for one or more selected rows.
- Copy selected paths.
- Copy complete selected rows as tab-separated data for spreadsheets.
- Export all results to a UTF-8 BOM CSV file for Excel compatibility.

### Interface, localization, and support

- Modern PySide6/Qt 6 interface.
- Light and dark themes.
- English is the default language for new or reset settings.
- 13 bundled interface languages:
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
- Localized menus, controls, messages, status text, and bug-report email drafts.
- One log file per application session.
- Background update check against the GitHub `VERSION.json` file.
- Manual update check with an explicit result message.
- GitHub, author email, issue-reporting, and sponsorship links.

## Safety and privacy

- Files and hashes are processed locally.
- HashSieve does not upload scanned files, paths, or hash results.
- The optional update check only requests the public `VERSION.json` file from GitHub.
- Deletion applies only to the rows currently selected by the user.
- Recycle Bin mode is enabled by default.
- 0-byte files are protected from duplicate grouping by default because empty placeholders such as `__init__.py` may still be meaningful.

Always review the selected paths before deleting files. HashSieve is a cleanup aid, not a substitute for backups.

## Download and run

### Windows release

Download `HashSieve.exe` from the [GitHub Releases](https://github.com/dogs1231992/HashSieve/releases) page and launch it normally.

Do **not** run HashSieve as Administrator unless Windows File Explorer is also elevated. Windows blocks drag and drop from a normal Explorer window into an elevated application.

### Run from source with the isolated conda launcher

From a normal, non-Administrator terminal:

```powershell
.\run_conda_env.bat
```

The launcher creates or reuses a `hashsieve-gui` environment with Python 3.11 and the pinned PySide6 build.

After the environment exists, the equivalent manual commands are:

```powershell
conda activate hashsieve-gui
python main.py
```

Another clean conda environment may also be used when PySide6 imports correctly:

```powershell
conda activate python_310_AI
python main.py
```

### Run from a local virtual environment

```powershell
.\run_clean_venv.bat
```

### Manual installation

```powershell
python -m pip install -r requirements.txt
python main.py
```

Avoid installing or running PySide6 from a heavily customized Anaconda `base` environment. Mixed Qt, PyQt, PySide6, and shiboken DLLs can cause `DLL load failed while importing QtCore` errors.

## Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Add files |
| `Ctrl+E` | Export CSV |
| `Ctrl+A` | Select all visible rows |
| `Ctrl+C` | Copy all selected rows as tab-separated data |
| `Delete` | Delete selected files |
| `Ctrl+Q` | Exit |
| Double-click a row | Open the containing folder and select the file |

## Build the Windows EXE

Run:

```powershell
.\build_windows.bat
```

The build script:

1. Creates or reuses an isolated Python 3.11 build environment.
2. Installs the pinned dependencies.
3. Verifies the PySide6, send2trash, and PyInstaller imports.
4. Builds a one-file, windowed EXE with PyInstaller.
5. Generates SHA-256 and SHA-512 checksum files.
6. Removes temporary `build`, `dist`, `.build_venv`, and `__pycache__` folders.

Release output:

```text
release\HashSieve.exe
release\HashSieve.exe.sha256
release\HashSieve.exe.sha512
release\CHECKSUMS.txt
```

Upload all four files as GitHub Release assets.

### Verify a downloaded EXE

PowerShell:

```powershell
Get-FileHash .\HashSieve.exe -Algorithm SHA256
Get-FileHash .\HashSieve.exe -Algorithm SHA512
```

Compare the results with `CHECKSUMS.txt` from the same GitHub Release. Checksums must be regenerated whenever the EXE is rebuilt.

MD5, SHA-1, and CRC32 are included in the application for duplicate comparison and interoperability. For release-file integrity verification, use the published SHA-256 or SHA-512 values.

## Pre-release validation

Run:

```powershell
python tools\check_locales.py
python tools\self_test.py
```

The bundled tests cover:

- Locale key and placeholder consistency across all 13 languages
- Version metadata consistency
- Worker limits and settings recovery
- Recursive scanning and path deduplication
- Hidden-file and symbolic-link behavior
- All six hash algorithms
- Exact duplicate grouping and 0-byte protection
- Keep-one selection and reclaimable-space calculations
- UTF-8 BOM CSV output
- Temporary-file deletion helper
- Group-color cycling, zebra rows, and selection-color contracts
- Large synthetic file-set stress testing

See [TESTING.md](TESTING.md) for the full validation checklist and Windows-only manual checks.

## Application data

On Windows, HashSieve stores its per-user data under:

```text
%APPDATA%\HashSieve\
```

Important files:

```text
%APPDATA%\HashSieve\settings.json
%APPDATA%\HashSieve\logs\HashSieve_YYYYMMDD_HHMMSS.log
```

A single log file is shared for the entire application session and closes when the application exits.

## Project structure

```text
app/core/              Scanning, hashing, grouping, CSV, and file operations
app/i18n/              Translation loader and locale JSON files
app/ui/                PySide6 main window, styles, widgets, and workers
app/utils/             Settings, paths, logging, and formatting helpers
assets/                 Application icons and theme assets
tools/                  Locale checker and pre-release self-test
HashSieve.spec          PyInstaller configuration
build_windows.bat       Isolated Windows release build
VERSION.json            Public update metadata
version_info.txt        Windows EXE version resource
```

## Troubleshooting

### `DLL load failed while importing QtCore`

Use the isolated launcher:

```powershell
.\run_conda_env.bat
```

Or rebuild a clean environment:

```powershell
conda env remove -n hashsieve-gui -y
.\run_conda_env.bat
```

### Drag and drop does not work

Close the elevated terminal or elevated HashSieve process, then launch HashSieve normally. Explorer and HashSieve must run at the same Windows integrity level.

### Update check shows no automatic message

Automatic checks are intentionally silent when the installed version is current or GitHub cannot be reached. Use **Help → Check for Updates** for a visible result.

### A file cannot be deleted

The file may be open, protected, read-only, locked by another process, or inaccessible with the current user permissions. Review the session log for the recorded error.

## Release history

- `v2.2026.07.19` — Modern PySide6 GUI, improved table workflow, themes, localization, settings resilience, and release hardening; core duplicate logic retained.
- `v1.2026.07.04` — Initial Tkinter release with recursive scanning, six hashes, exact duplicate grouping, CSV export, and reviewed deletion.

See [CHANGELOG.md](CHANGELOG.md) for full details.

## Links

- GitHub repository: https://github.com/dogs1231992/HashSieve
- GitHub Releases: https://github.com/dogs1231992/HashSieve/releases
- Report a bug or request a feature: https://github.com/dogs1231992/HashSieve/issues/new
- Sponsor: GitHub Sponsors — https://github.com/sponsors/dogs1231992
- Sponsor: Buy Me a Coffee — https://buymeacoffee.com/dogs1231992
- Author: Shih-Han Wang
- Email: wangsh@vt.edu

## License

HashSieve is released under the [MIT License](LICENSE).

HashSieve is an independent project and is not affiliated with NirSoft HashMyFiles or other third-party utilities. Product names are mentioned only to describe comparable workflows.
