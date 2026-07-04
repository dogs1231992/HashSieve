# HashSieve v1.2026.07.04

HashSieve is a local-first Windows desktop tool for recursively scanning files and folders, calculating multiple file hashes, grouping exact duplicate files, exporting CSV reports, and safely cleaning duplicate copies after user review.

## Highlights

- Drag-and-drop files, folders, or mixed file/folder input.
- Recursive folder scanning, including subfolders and deeper nested folders.
- Automatic hash calculation after files/folders are added.
- Computes MD5, SHA-1, CRC32, SHA-256, SHA-384, and SHA-512.
- Groups duplicates only when file size and all six hash values are identical.
- 0-byte empty files are listed and hashed, but ignored for duplicate grouping by default.
- Large-folder friendly pipeline with background scanning, bounded worker-thread hashing, and one final result-table build.
- Progress display with file count, total size, files/second, and bytes/second.
- Review-first duplicate cleanup: select duplicates except one, adjust the selection, then delete selected files.
- Recycle Bin deletion by default, with optional permanent delete confirmation.
- CSV export with UTF-8 BOM for Excel compatibility.
- Sort indicators, column resizing, column reordering, saved table layout, light/dark themes, and multilingual UI.

## Release assets

Download `HashSieve.exe` for the Windows one-file build.

For verification, also download:

- `HashSieve.exe.sha256`
- `HashSieve.exe.sha512`
- `CHECKSUMS.txt`

## Checksums

```text
SHA256  <replace with generated SHA-256>  HashSieve.exe
SHA512  <replace with generated SHA-512>  HashSieve.exe
```

## Notes

HashSieve is an independent project. It is not affiliated with NirSoft HashMyFiles or any other third-party tool. Product names are mentioned only to describe comparable workflows.
