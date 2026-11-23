"""CLI: python -m engine.run generate|build|distribute|report|feeds [--sites id1,id2]"""
from __future__ import annotations

import argparse
import sys
import time

from .build import build_site, load_articles
from .collect import collect, fetch_feed, fetch_fulltext, mark_seen
from .common import STATE_DIR, load_sites, log, read_json, write_json
from .distribute import distribute, notify_admin
from .gemini import Gemini, QuotaExhausted
from .rewrite import rewrite


def cmd_generate(sites) -> int:
    gem = Gemini.get()
    total = 0
    for cfg in sites:
        log(f"[{cfg['id']}] збір джерел")
        items = collect(cfg)
        log(f"[{cfg['id']}] нових кандидатів: {len(items)}")
        made, tried = 0, 0
        for it in items:
            if made >= cfg["max_new_per_run"] or tried >= cfg["max_new_per_run"] * 3:
                break
            tried += 1
            full = fetch_fulltext(it["link"])
            try:
                res = rewrite(cfg, it, full, gem)
            except QuotaExhausted:
                log("Gemini: ліміт на всіх ключах — стоп, продовжимо наступним прогоном")
                return total
            except Exception as e:  # noqa: BLE001 — одна битa новина не валить весь прогін, але логуємо
                log(f"  ✗ {it['title'][:70]}: {type(e).__name__}: {e}")
                mark_seen(cfg, it)
                continue
            mark_seen(cfg, it)
            if res and res.get("skip"):
                log(f"  – пропуск: {it['title'][:70]} ({res.get('reason')})")
                continue
            made += 1
            total += 1
            log(f"  + {res['langs'][cfg['default_lang']]['title'][:80]}")
        log(f"[{cfg['id']}] нових статей: {made}")
    log(f"Gemini запитів: {gem.calls}, нових статей усього: {total}")
    return total


def cmd_build(sites) -> None:
    for cfg in sites:
        build_site(cfg)


def cmd_distribute(sites) -> None:
    errors = []
    for cfg in sites:
        errors += distribute(cfg)
    if errors:
        # не спамимо однаковою помилкою: шлемо, якщо змінився набір помилок
        st = STATE_DIR / "_alerts.json"
        prev = read_json(st, {})
        sig = "|".join(sorted(e[:60] for e in errors))
        if prev.get("sig") != sig or time.time() - prev.get("ts", 0) > 12 * 3600:
            notify_admin("⚠️ newsfactory: помилки автопостингу\n\n" + "\n".join(errors[:15]))
            write_json(st, {"sig": sig, "ts": time.time()})


def cmd_report(sites) -> None:
    week = time.time() - 7 * 86400
    lines = ["📊 newsfactory — тиждень"]
    for cfg in sites:
        arts = load_articles(cfg["id"])
        n = sum(1 for a in arts if a["created"] >= week)
        posted = read_json(STATE_DIR / cfg["id"] / "posted.json", {})
        p = sum(len(v) for k, v in posted.items())
        lines.append(f"• {cfg['name']}: +{n} статей (усього {len(arts)}), постів у соцмережах: {p}")
    notify_admin("\n".join(lines))
    print("\n".join(lines))


def cmd_feeds(sites) -> None:
    bad = []
    for cfg in sites:
        for src in cfg.get("sources", []):
            url = src if isinstance(src, str) else src["url"]
            n = len(fetch_feed(url))
            print(f"{cfg['id']:10} {n:>3}  {url}")
            if n == 0:
                bad.append(f"{cfg['id']}: {url}")
    if bad:
        notify_admin("RSS без свіжих новин або недоступні:\n" + "\n".join(bad))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["generate", "build", "distribute", "report", "feeds"])
    ap.add_argument("--sites", default="")
    a = ap.parse_args()
    sites = load_sites([s for s in a.sites.split(",") if s] or None)
    if not sites:
        sys.exit("немає сайтів")
    {"generate": cmd_generate, "build": cmd_build, "distribute": cmd_distribute,
     "report": cmd_report, "feeds": cmd_feeds}[a.cmd](sites)


if __name__ == "__main__":
    main()
