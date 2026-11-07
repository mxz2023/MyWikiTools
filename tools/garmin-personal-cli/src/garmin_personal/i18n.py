"""Lightweight i18n: LANG from env or --lang preparsed from argv."""

from __future__ import annotations

import os
import sys

Lang = str  # "both" | "en" | "zh"


def _read_lang_from_argv() -> Lang:
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--lang" and i + 1 < len(argv):
            return argv[i + 1] or "both"
        if a.startswith("--lang="):
            return a.split("=", 1)[1] or "both"
    env = os.environ.get("GARMIN_CLI_LANG") or os.environ.get("LANG", "")
    if env.startswith("zh"):
        return "both"  # default doc still bilingual unless explicit GARMIN_CLI_LANG
    if os.environ.get("GARMIN_CLI_LANG") in ("en", "zh", "both"):
        return os.environ["GARMIN_CLI_LANG"]
    return "both"


LANG: Lang = _read_lang_from_argv()


def T(en: str, zh: str) -> str:
    if LANG == "en":
        return en
    if LANG == "zh":
        return zh
    return f"{en} / {zh}"
