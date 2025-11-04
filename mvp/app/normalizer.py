from typing import Dict, Any, List
import json, os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "synonyms_ptbr.json")

def load_synonyms() -> Dict[str, str]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

SYNONYMS = load_synonyms()

def normalize_text(text: str) -> str:
    if not text:
        return text
    t = text.lower()
    for k, v in SYNONYMS.items():
        t = t.replace(k.lower(), v)
    # capitalize basic
    return t[0].upper() + t[1:] if len(t) > 1 else t

def normalize_bullets(bullets: List[str]) -> List[str]:
    return [normalize_text(b) for b in bullets] if bullets else []

def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(payload)
    p["queixa_principal"] = normalize_text(p.get("queixa_principal", ""))
    p["bullets"] = normalize_bullets(p.get("bullets", []))
    return p
