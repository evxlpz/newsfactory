"""Розсилка свіжих статей у всі ввімкнені соцмережі/месенджери сайту."""
from __future__ import annotations

import html
import os
import time

import requests

from ..build import art_path, load_articles
from ..cards import CACHE
from ..common import STATE_DIR, brand, log, read_json, site_url, write_json
from ..i18n import t
from .channels import CHANNELS, ChannelError

MAX_AGE_H = 8          # не постимо старе (щоб не було спаму беклогом)
MAX_PER_CHANNEL = 3    # за один прогін


def notify_admin(text: str) -> None:
    token, chat = os.environ.get("TG_BOT_TOKEN"), os.environ.get("ADMIN_TG_CHAT")
    if not token or not chat:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      data={"chat_id": chat, "text": text[:4000]}, timeout=20)
    except requests.RequestException as e:
        log(f"admin notify failed: {e}")


def distribute(cfg: dict) -> list[str]:
    errors: list[str] = []
    socials = cfg.get("socials") or []
    if not socials:
        return errors
    state_path = STATE_DIR / cfg["id"] / "posted.json"
    posted = read_json(state_path, {})
    base = site_url(cfg)
    fresh = [a for a in load_articles(cfg["id"]) if time.time() - a["created"] < MAX_AGE_H * 3600]
    fresh.reverse()  # старші першими — правильний порядок у стрічці

    for conf in socials:
        cls = CHANNELS.get(conf.get("type"))
        if not cls:
            continue
        ch = cls(conf)
        lang = ch.lang or cfg["default_lang"]
        ch.lang = lang
        if not ch.enabled():
            continue
        key = f"{conf['type']}:{lang}"
        done = 0
        for a in fresh:
            if done >= MAX_PER_CHANNEL:
                break
            if lang not in a["langs"] or key in posted.get(a["id"], {}):
                continue
            v = a["langs"][lang]
            img_key = f"{a['id']}-{lang}"
            p = {
                "title": v["title"], "dek": v["dek"], "social": v["social"],
                "title_html": html.escape(v["title"]), "social_html": html.escape(v["social"]),
                "url": base + art_path(cfg, lang, a), "img_url": f"{base}/img/{img_key}.png",
                "img_path": str(CACHE / cfg["id"] / f"{img_key}.png"),
                "read_more": t(lang)["read_more"], "link_hint": f"{brand(cfg, lang)} — {base.replace('https://', '')}",
            }
            try:
                pid = ch.post(p)
                posted.setdefault(a["id"], {})[key] = pid
                done += 1
                log(f"  → {key} ✓ {v['title'][:60]}")
            except (ChannelError, requests.RequestException, OSError, KeyError) as e:
                msg = f"[{cfg['id']}] {key}: {e}"
                log("  ✗ " + msg)
                errors.append(msg)
                break  # канал зламаний — не пробуємо решту статей цього разу
            write_json(state_path, posted)
    # прибираємо старі записи
    cutoff = {a["id"] for a in load_articles(cfg["id"])[:500]}
    write_json(state_path, {k: v for k, v in posted.items() if k in cutoff})
    return errors
