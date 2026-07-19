# HashSieve v2.2026.07.19

HashSieve v2 is a major GUI modernization release. It replaces the original Tkinter interface with a modern PySide6/Qt 6 interface while preserving the v1 recursive scanning, hashing, exact duplicate rule, CSV export, and reviewed deletion workflow.

## Highlights

- Modern card-based PySide6/Qt 6 interface.
- Light and dark themes.
- Ten repeating full-row colors for duplicate groups.
- Neutral zebra rows for files outside duplicate groups.
- One unified selected-row color per theme; deselecting restores the original row color.
- Six hashes calculated in one pass: MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512.
- Exact duplicate rule: file size and all six hashes must match.
- Worker count limited to the machine's logical CPU count.
- Background scan/hash pipeline with file, byte, files/s, and bytes/s progress.
- Five strategies for deciding which file to keep in each duplicate group.
- CSV export, full-row copy, path copy, individual hash copy, and Explorer file selection.
- 13 interface languages with English as the default for new or reset settings.
- More reliable settings recovery, deterministic keep-first behavior, symbolic-link cycle protection, and numeric update comparison.

## Safety defaults

- Hidden files are excluded.
- Symbolic links are not followed.
- 0-byte files are listed and hashed but excluded from duplicate groups.
- Selected files are moved to the Recycle Bin rather than permanently deleted.

All options can be changed from the main interface or View menu.

## Upgrade notes

Version 2 uses a new PySide6 interface and a newer preferences schema. Incompatible v1 GUI preferences are replaced once with clean v2 defaults. This does not modify scanned files.

Run HashSieve normally rather than as Administrator so drag and drop from Windows File Explorer remains available.

## Release assets

Download all verification files from the same release:

- `HashSieve.exe`
- `HashSieve.exe.sha256`
- `HashSieve.exe.sha512`
- `CHECKSUMS.txt`

Verify the EXE with PowerShell:

```powershell
Get-FileHash .\HashSieve.exe -Algorithm SHA256
Get-FileHash .\HashSieve.exe -Algorithm SHA512
```

Compare the output with `CHECKSUMS.txt` attached to this release.

## Full details

See the [README](https://github.com/dogs1231992/HashSieve#readme) for installation and usage, the [changelog](https://github.com/dogs1231992/HashSieve/blob/main/CHANGELOG.md) for the complete change history, and the [validation report](https://github.com/dogs1231992/HashSieve/blob/main/TESTING.md) for the release checklist.
