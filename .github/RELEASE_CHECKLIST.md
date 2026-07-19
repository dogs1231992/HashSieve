# HashSieve v2.2026.07.19 release checklist

## Source

- [ ] Confirm `git status` contains only intended changes.
- [ ] Confirm no `build/`, `dist/`, `release/`, `.build_venv/`, `__pycache__/`, `.pyc`, logs, or local settings are committed.
- [ ] Search for stale version references:

```powershell
Get-ChildItem -Recurse -File | Select-String "v2\.2026\."
```

- [ ] Run:

```powershell
python tools\check_locales.py
python tools\self_test.py
```

- [ ] Complete the Windows manual checks in `TESTING.md`.

## Commit and tag

Suggested commit:

```powershell
git add .
git commit -m "Release HashSieve v2.2026.07.19"
git push origin main
```

Create the tag only after the final commit is pushed:

```powershell
git tag v2.2026.07.19
git push origin v2.2026.07.19
```

## Build

Run from a normal PowerShell window:

```powershell
.\build_windows.bat
```

Confirm these files were created:

```text
release\HashSieve.exe
release\HashSieve.exe.sha256
release\HashSieve.exe.sha512
release\CHECKSUMS.txt
```

Launch the final EXE and repeat the critical smoke tests before uploading it.

## GitHub Release

- Tag: `v2.2026.07.19`
- Target: `main`
- Title: `HashSieve v2.2026.07.19`
- Pre-release: No
- Set as latest release: Yes
- Release notes: use `RELEASE_NOTES_v2.2026.07.19.md`
- Upload all four files from `release/`.

Never copy checksums from an earlier build. Use only the checksum files generated beside the final uploaded EXE.
