# HashSieve localization files

Each JSON file in this folder maps an internal English UI key to the displayed text for one language.

The language packs bundled with `v2.2026.07.19` cover every runtime UI key used by HashSieve. Technical names such as Hash, CSV, MD5, SHA-256, GitHub, GitHub Sponsors, and Buy Me a Coffee may remain in English when that is clearer, but the surrounding action or sponsor context should be translated.

## Bundled languages

- `en-US` — English
- `zh-TW` — 繁體中文
- `zh-CN` — 简体中文
- `ja-JP` — 日本語
- `ko-KR` — 한국어
- `es-ES` — Español
- `fr-FR` — Français
- `de-DE` — Deutsch
- `pt-BR` — Português (Brasil)
- `ru-RU` — Русский
- `th-TH` — ไทย
- `id-ID` — Bahasa Indonesia
- `ar-SA` — العربية

## Editing rules

1. Keep every JSON key unchanged.
2. Translate only the JSON values.
3. Preserve placeholders exactly, including names and braces, for example `{count}`, `{size}`, `{path}`, `{version}`, and `{log_content}`.
4. Preserve intentional product names and hash algorithm names.
5. Keep native language names in `app/i18n/translator.py` so users never have to choose from locale codes.
6. Save files as UTF-8 JSON.
7. Do not add comments inside JSON files.
8. Run the locale checker after every translation change:

```powershell
python tools\check_locales.py
```

The checker verifies required keys and placeholder consistency against `en-US.json`.
