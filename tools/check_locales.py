# -*- coding: utf-8 -*-
"""Check that all HashSieve locale JSON files contain the UI keys used by the app."""
from __future__ import annotations

import ast
import json
import string
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE_DIR = ROOT / "app" / "i18n" / "locales"

# Keys used dynamically in main_window.py rather than as literal t("...") calls.
DYNAMIC_KEYS = {
    "Files",
    "Duplicate groups",
    "Duplicate files",
    "Reclaimable",
    "Workers",
    "Keep",
    "Keep first file in each group",
    "Keep oldest modified file",
    "Keep newest modified file",
    "Keep shortest path",
    "Keep longest path",
    "View",
    "Warning",
    "Some files could not be read",
}


def collect_literal_t_keys() -> set[str]:
    keys: set[str] = set()
    for py_file in (ROOT / "app").rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            is_t_call = (
                isinstance(func, ast.Attribute) and func.attr in {"t", "_set_status"}
            ) or (
                isinstance(func, ast.Name) and func.id in {"t", "_set_status"}
            )
            if is_t_call and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                keys.add(node.args[0].value)
    return keys


def _placeholders(text: str) -> list[str]:
    formatter = string.Formatter()
    return sorted(field_name for _literal, field_name, _spec, _conversion in formatter.parse(text) if field_name is not None)


def main() -> int:
    required = collect_literal_t_keys() | DYNAMIC_KEYS
    ok = True
    fallback = json.loads((LOCALE_DIR / "en-US.json").read_text(encoding="utf-8"))
    for locale_file in sorted(LOCALE_DIR.glob("*.json")):
        data = json.loads(locale_file.read_text(encoding="utf-8"))
        missing = sorted(required - set(data))
        if missing:
            ok = False
            print(f"{locale_file.name}: missing {len(missing)} key(s)")
            for key in missing:
                print(f"  - {key}")
        for key in sorted(required & set(data) & set(fallback)):
            try:
                expected = _placeholders(fallback[key])
                actual = _placeholders(data[key])
            except ValueError as exc:
                ok = False
                print(f"{locale_file.name}: invalid format string for {key!r}: {exc}")
                continue
            if actual != expected:
                ok = False
                print(f"{locale_file.name}: placeholder mismatch for {key!r}: expected {expected}, found {actual}")
    if ok:
        print(f"OK: {len(required)} required UI keys and their placeholders are valid in every locale file.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
