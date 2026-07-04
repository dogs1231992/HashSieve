from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from .app_paths import resource_path

SUPPORTED_LANGUAGES: dict[str, str] = {
    "en-US": "English",
    "zh-TW": "繁體中文",
    "zh-CN": "简体中文",
    "ja-JP": "日本語",
    "ko-KR": "한국어",
    "es-ES": "Español",
    "fr-FR": "Français",
    "de-DE": "Deutsch",
    "pt-BR": "Português (Brasil)",
    "ru-RU": "Русский",
    "th-TH": "ไทย",
    "id-ID": "Bahasa Indonesia",
    "ar-SA": "العربية",
}


class Translator:
    def __init__(self, language: str = "en-US") -> None:
        self.language = language if language in SUPPORTED_LANGUAGES else "en-US"
        self._strings: Dict[str, str] = {}
        self.load(self.language)

    def load(self, language: str) -> None:
        self.language = language if language in SUPPORTED_LANGUAGES else "en-US"
        self._strings = {}
        path = resource_path(f"locales/{self.language}.json")
        if path.exists():
            try:
                self._strings = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self._strings = {}

    def t(self, key: str, fallback: str | None = None) -> str:
        # Always consult the locale file, including en-US. This allows labels such
        # as "Sponsor: Buy Me a Coffee" to be different from the internal key.
        return self._strings.get(key, fallback if fallback is not None else key)
