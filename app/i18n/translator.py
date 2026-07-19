# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

DEFAULT_LANGUAGE = "en-US"
LANGUAGE_NAMES: Dict[str, str] = {
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
    def __init__(self, locales_dir: Path | str, language: str = DEFAULT_LANGUAGE):
        self.locales_dir = Path(locales_dir)
        self._cache: Dict[str, Dict[str, str]] = {}
        self.default_language = DEFAULT_LANGUAGE
        self.current_language = language if language in self.available_languages() else DEFAULT_LANGUAGE
        self._fallback = self._load(DEFAULT_LANGUAGE)
        self._active = self._load(self.current_language)

    def _load(self, lang_code: str) -> Dict[str, str]:
        if lang_code in self._cache:
            return self._cache[lang_code]
        path = self.locales_dir / f"{lang_code}.json"
        data: Dict[str, str] = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        self._cache[lang_code] = data
        return data

    def set_language(self, lang_code: str) -> None:
        self.current_language = lang_code
        self._active = self._load(lang_code)

    def available_languages(self) -> List[str]:
        if not self.locales_dir.exists():
            return [DEFAULT_LANGUAGE]
        preferred = list(LANGUAGE_NAMES.keys())
        available = {p.stem for p in self.locales_dir.glob("*.json")}
        ordered = [x for x in preferred if x in available]
        extras = sorted(available - set(ordered))
        return ordered + extras or [DEFAULT_LANGUAGE]

    def language_display_name(self, lang_code: str) -> str:
        return LANGUAGE_NAMES.get(lang_code, lang_code)

    def t(self, key: str, fallback: str | None = None, **kwargs) -> str:
        text = self._active.get(key) or self._fallback.get(key) or fallback or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text
