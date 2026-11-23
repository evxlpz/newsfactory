"""Спільні утиліти: шляхи, конфіги сайтів, JSON, slug, лог."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SITES_DIR = ROOT / "sites"
CONTENT_DIR = ROOT / "content"
STATE_DIR = ROOT / "state"
OUT_DIR = ROOT / "out"
TEMPLATES_DIR = ROOT / "templates"
STATIC_DIR = ROOT / "static"

# У GitHub Actions усі Secrets приходять одним JSON (toJSON(secrets)) — розкладаємо в env,
# щоб нові ключі/токени працювали без правки workflow.
if os.environ.get("SECRETS_JSON"):
    for _k, _v in json.loads(os.environ["SECRETS_JSON"]).items():
        if isinstance(_v, str) and _k not in os.environ:
            os.environ[_k] = _v

LANG_NAMES = {
    "uk": "Українська", "en": "English", "pl": "Polski",
    "es": "Español", "fr": "Français", "de": "Deutsch",
    "it": "Italiano", "pt": "Português",
}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def load_sites(only: list[str] | None = None) -> list[dict]:
    sites = []
    for f in sorted(SITES_DIR.glob("*/site.yaml")):
        cfg = yaml.safe_load(f.read_text(encoding="utf-8"))
        cfg["id"] = f.parent.name
        if only and cfg["id"] not in only:
            continue
        if cfg.get("enabled", True) is False:
            continue
        cfg.setdefault("langs", ["uk", "en"])
        cfg.setdefault("default_lang", cfg["langs"][0])
        cfg.setdefault("max_new_per_run", 2)
        cfg.setdefault("socials", {})
        sites.append(cfg)
    return sites


def brand(cfg: dict, lang: str) -> str:
    """Назва видання: кирилицею для uk, латиницею для інших мов."""
    return cfg["name"] if lang == "uk" else cfg.get("name_latin") or cfg["name"]


def site_url(cfg: dict) -> str:
    """Базовий URL сайту: свій домен, якщо є, інакше pages.dev."""
    domain = cfg.get("domain") or f"{cfg['pages_project']}.pages.dev"
    return f"https://{domain}".rstrip("/")


def read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def sha(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


_UK = {
    "а": "a", "б": "b", "в": "v", "г": "h", "ґ": "g", "д": "d", "е": "e", "є": "ie",
    "ж": "zh", "з": "z", "и": "y", "і": "i", "ї": "i", "й": "i", "к": "k", "л": "l",
    "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ь": "",
    "ю": "iu", "я": "ia", "'": "", "’": "", "ʼ": "",
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ź": "z", "ż": "z",
}


def slugify(text: str, max_len: int = 70) -> str:
    text = text.lower()
    text = "".join(_UK.get(ch, ch) for ch in text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rsplit("-", 1)[0]
    return text or "post"


def env_list(prefix: str) -> list[str]:
    """Збирає PREFIX, PREFIX_2, PREFIX_3 ... (наприклад кілька ключів Gemini)."""
    vals = []
    for k, v in sorted(os.environ.items()):
        if (k == prefix or re.fullmatch(rf"{prefix}_\d+", k)) and v.strip():
            vals.append(v.strip())
    return vals
