"""Збір новин з RSS джерел сайту + витяг повного тексту статті."""
from __future__ import annotations

import calendar
import html
import re
import time

import feedparser
import requests

from .common import STATE_DIR, log, read_json, sha, write_json

UA = "Mozilla/5.0 (compatible; NewsfactoryBot/1.0)"
MAX_AGE_H = 36
_session = requests.Session()
_session.headers["User-Agent"] = UA


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _words(title: str) -> set[str]:
    return {w for w in re.findall(r"\w{4,}", title.lower())}


def _similar(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= 0.5


def fetch_feed(url: str) -> list[dict]:
    try:
        r = _session.get(url, timeout=25)
        r.raise_for_status()
    except requests.RequestException as e:
        log(f"  RSS помилка {url}: {e}")
        return []
    feed = feedparser.parse(r.content)
    items = []
    now = time.time()
    for e in feed.entries[:40]:
        link = e.get("link")
        title = _clean(e.get("title", ""))
        if not link or not title:
            continue
        ts = None
        for key in ("published_parsed", "updated_parsed"):
            if e.get(key):
                ts = calendar.timegm(e[key])
                break
        if ts and now - ts > MAX_AGE_H * 3600:
            continue
        summary = _clean(e.get("summary", "") or e.get("description", ""))
        items.append({"title": title, "link": link, "summary": summary[:1500],
                      "ts": ts or now, "source": feed.feed.get("title", url)})
    return items


def fetch_fulltext(url: str) -> str:
    """Повний текст статті (trafilatura). Якщо не вийшло — порожньо, беремо summary з RSS."""
    try:
        import trafilatura
        r = _session.get(url, timeout=25)
        if r.status_code != 200:
            return ""
        text = trafilatura.extract(r.text, include_comments=False, include_tables=False) or ""
        return text[:7000]
    except Exception as e:  # noqa: BLE001 — логуємо і йдемо далі з summary
        log(f"  fulltext не витягнувся {url}: {type(e).__name__}: {e}")
        return ""


def collect(cfg: dict) -> list[dict]:
    """Нові, не бачені раніше новини, без дублів між джерелами. Найсвіжіші першими, по черзі з різних джерел."""
    state_path = STATE_DIR / cfg["id"] / "seen.json"
    state = read_json(state_path, {"links": [], "titles": []})
    seen_links = set(state["links"])
    recent_titles = [set(t.split()) for t in state["titles"][-400:]]

    per_source: list[list[dict]] = []
    for src in cfg.get("sources", []):
        url = src if isinstance(src, str) else src["url"]
        items = fetch_feed(url)
        log(f"  {len(items):>3} свіжих  {url}")
        items = [i for i in items if sha(i["link"]) not in seen_links]
        items.sort(key=lambda i: -i["ts"])
        per_source.append(items)

    # round-robin, щоб одне джерело не забивало стрічку
    merged, k = [], 0
    while any(k < len(s) for s in per_source):
        for s in per_source:
            if k < len(s):
                merged.append(s[k])
        k += 1

    out = []
    batch_titles: list[set[str]] = []
    for it in merged:
        w = _words(it["title"])
        if any(_similar(w, t) for t in recent_titles + batch_titles):
            continue
        batch_titles.append(w)
        out.append(it)
    return out


def mark_seen(cfg: dict, item: dict) -> None:
    state_path = STATE_DIR / cfg["id"] / "seen.json"
    state = read_json(state_path, {"links": [], "titles": []})
    state["links"] = (state["links"] + [sha(item["link"])])[-3000:]
    state["titles"] = (state["titles"] + [" ".join(sorted(_words(item["title"])))])[-600:]
    write_json(state_path, state)
