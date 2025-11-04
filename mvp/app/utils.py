"""Utility helpers for the medical writing assistant."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable

try:  # Optional high-performance serializer
    import orjson  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    orjson = None  # type: ignore

try:
    import streamlit as st
except Exception:  # pragma: no cover - streamlit not required for tests
    st = None  # type: ignore

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
GLOSSARY_FILE = DATA_DIR / "synonyms_ptbr.json"


def _load_glossary() -> Dict[str, str]:
    if not GLOSSARY_FILE.exists():
        return {}
    with GLOSSARY_FILE.open("r", encoding="utf-8") as fp:
        return json.load(fp)


if st is not None:

    @st.cache_data(show_spinner=False)
    def load_glossary() -> Dict[str, str]:
        return _load_glossary()

else:  # pragma: no cover - executed during tests where streamlit may not be loaded

    def load_glossary() -> Dict[str, str]:
        return _load_glossary()


def sanitize_text(text: str) -> str:
    """Normalise whitespace and ensure consistent line breaks."""
    if not text:
        return ""
    sanitized = " ".join(text.replace("\r", "").split())
    return sanitized.strip()


def normalize_text(text: str) -> str:
    if not text:
        return ""
    glossary = load_glossary()
    lowered = text.lower()
    for original, normalized in glossary.items():
        lowered = lowered.replace(original.lower(), normalized)
    if not lowered:
        return lowered
    return lowered[0].upper() + lowered[1:]


def normalize_bullets(bullets: Iterable[str] | None) -> list[str]:
    if not bullets:
        return []
    return [normalize_text(item) for item in bullets if item]


def ensure_directories(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def dumps_json(data: Any, compact: bool = False) -> bytes:
    if orjson is not None:
        option = orjson.OPT_INDENT_2 if not compact else orjson.OPT_OMIT_MICROSECONDS
        return orjson.dumps(data, option=option)
    text = json.dumps(data, ensure_ascii=False, indent=None if compact else 2)
    return text.encode("utf-8")


def make_cache_key(*parts: str, params: Dict[str, Any] | None = None) -> str:
    payload = "::".join(parts)
    if params:
        try:
            params_blob = json.dumps(params, sort_keys=True, ensure_ascii=False)
        except TypeError:
            params_blob = json.dumps(str(params))
        payload += f"::{params_blob}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_export_path(folder: Path, prefix: str, suffix: str) -> Path:
    ensure_directories(folder)
    safe_prefix = sanitize_text(prefix).replace(" ", "_") or "documento"
    counter = 0
    while True:
        candidate = folder / f"{safe_prefix}-{counter:02d}.{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def read_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def write_json_file(path: Path, data: Dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)
