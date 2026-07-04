# HashSieve localization files

Each JSON file in this folder maps the internal English UI key to the display string for one language.

The bundled language packs for `v1.2026.07.04` include every runtime UI key used by the application. Technical/product terms such as Hash, CSV, GitHub, and Buy Me a Coffee may remain in English where appropriate, but menu labels include local-language context such as sponsor prefixes.

When adding or updating a language:

1. Keep the JSON keys unchanged.
2. Translate only the values.
3. Preserve placeholders exactly, for example `{count}`, `{size}`, `{path}`, `{version}`, `{log_content}`.
4. Preserve intentional product names such as GitHub Sponsors and Buy Me a Coffee.
5. Use native language names in `core/i18n.py` so users can choose their language without reading locale codes.
6. Run a JSON/locale key check before release.
