# -*- coding: utf-8 -*-
from __future__ import annotations

APP_NAME = "HashSieve"
APP_DISPLAY_NAME = "HashSieve"
APP_VERSION = "v2.2026.07.19"
AUTHOR_NAME = "Shih-Han Wang"
AUTHOR_EMAIL = "wangsh@vt.edu"
GITHUB_REPO_URL = "https://github.com/dogs1231992/HashSieve"
GITHUB_ISSUES_URL = GITHUB_REPO_URL + "/issues/new"
GITHUB_README_URL = GITHUB_REPO_URL + "#readme"
GITHUB_RELEASES_URL = GITHUB_REPO_URL + "/releases"
UPDATE_VERSION_URL = "https://raw.githubusercontent.com/dogs1231992/HashSieve/main/VERSION.json"
SPONSOR_URL = "https://github.com/sponsors/dogs1231992"
BUYMEACOFFEE_URL = "https://www.buymeacoffee.com/dogs1231992"
LICENSE_NAME = "MIT License"
EMAIL_SUBJECT_DEFAULT = f"[{APP_NAME}] feedback"


def parse_version(version: str) -> tuple[int, ...]:
    """Convert v2.2026.07.19-style versions to comparable numeric tuples."""
    parts: list[int] = []
    for token in str(version).strip().lstrip("vV").split("."):
        try:
            parts.append(int(token))
        except ValueError:
            break
    return tuple(parts)


def is_newer_version(candidate: str, current: str = APP_VERSION) -> bool:
    return bool(candidate and parse_version(candidate) > parse_version(current))


def get_about_text() -> str:
    return f"{APP_DISPLAY_NAME} {APP_VERSION}\n© {AUTHOR_NAME}"
