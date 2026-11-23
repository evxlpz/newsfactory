"""Канали автопостингу. Кожен канал вмикається, тільки коли в Secrets є його токени.

У site.yaml для каналу вказуються НАЗВИ secret-змінних (не самі токени):
  socials:
    telegram: {token_env: TG_BOT_TOKEN, chat_env: TG_CHAT_AITECH, lang: uk}
"""
from __future__ import annotations

import os
from pathlib import Path

import requests

GRAPH = "https://graph.facebook.com/v21.0"
THREADS = "https://graph.threads.net/v1.0"
_s = requests.Session()


class ChannelError(Exception):
    pass


def _env(conf: dict, key: str) -> str:
    name = conf.get(key)
    return os.environ.get(name, "").strip() if name else ""


def _check(r: requests.Response, what: str) -> dict:
    try:
        data = r.json()
    except ValueError:
        data = {"raw": r.text[:300]}
    if r.status_code >= 300 or (isinstance(data, dict) and data.get("ok") is False) or (
            isinstance(data, dict) and data.get("error")):
        raise ChannelError(f"{what}: HTTP {r.status_code} {str(data)[:300]}")
    return data


class Channel:
    name = "base"
    required: tuple[str, ...] = ()

    def __init__(self, conf: dict):
        self.conf = conf
        self.lang = conf.get("lang")

    def enabled(self) -> bool:
        return all(_env(self.conf, k) for k in self.required)

    def post(self, p: dict) -> str:  # повертає id/посилання поста
        raise NotImplementedError


class Telegram(Channel):
    name, required = "telegram", ("token_env", "chat_env")

    def post(self, p):
        token, chat = _env(self.conf, "token_env"), _env(self.conf, "chat_env")
        caption = f"<b>{p['title_html']}</b>\n\n{p['social_html']}\n\n<a href=\"{p['url']}\">{p['read_more']} →</a>"
        with open(p["img_path"], "rb") as f:
            r = _s.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                        data={"chat_id": chat, "caption": caption[:1024], "parse_mode": "HTML"},
                        files={"photo": f}, timeout=60)
        return str(_check(r, "telegram")["result"]["message_id"])


class Viber(Channel):
    """Viber-канал: Channels Post API (токен каналу + id суперадміна)."""
    name, required = "viber", ("token_env", "from_env")

    def post(self, p):
        r = _s.post("https://chatapi.viber.com/pa/post", headers={"X-Viber-Auth-Token": _env(self.conf, "token_env")},
                    json={"from": _env(self.conf, "from_env"), "type": "picture", "media": p["img_url"],
                          "text": f"{p['title']}\n\n{p['social']}\n\n{p['url']}"[:768]}, timeout=60)
        data = _check(r, "viber")
        if data.get("status") not in (0, None):
            raise ChannelError(f"viber: {data}")
        return str(data.get("message_token", ""))


class Facebook(Channel):
    name, required = "facebook", ("page_id_env", "token_env")

    def post(self, p):
        r = _s.post(f"{GRAPH}/{_env(self.conf, 'page_id_env')}/feed",
                    data={"message": f"{p['social']}", "link": p["url"],
                          "access_token": _env(self.conf, "token_env")}, timeout=60)
        return _check(r, "facebook")["id"]


class Instagram(Channel):
    name, required = "instagram", ("user_id_env", "token_env")

    def post(self, p):
        uid, tok = _env(self.conf, "user_id_env"), _env(self.conf, "token_env")
        caption = f"{p['title']}\n\n{p['social']}\n\n{p['link_hint']}"
        r = _s.post(f"{GRAPH}/{uid}/media", data={"image_url": p["img_url"], "caption": caption[:2200],
                                                  "access_token": tok}, timeout=60)
        cid = _check(r, "instagram media")["id"]
        r = _s.post(f"{GRAPH}/{uid}/media_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
        return _check(r, "instagram publish")["id"]


class Threads(Channel):
    name, required = "threads", ("user_id_env", "token_env")

    def post(self, p):
        uid, tok = _env(self.conf, "user_id_env"), _env(self.conf, "token_env")
        text = f"{p['title']}\n\n{p['social']}"[:480]
        r = _s.post(f"{THREADS}/{uid}/threads", data={"media_type": "TEXT", "text": text,
                                                     "link_attachment": p["url"], "access_token": tok}, timeout=60)
        cid = _check(r, "threads create")["id"]
        r = _s.post(f"{THREADS}/{uid}/threads_publish", data={"creation_id": cid, "access_token": tok}, timeout=60)
        return _check(r, "threads publish")["id"]


class Bluesky(Channel):
    name, required = "bluesky", ("handle_env", "password_env")
    PDS = "https://bsky.social/xrpc"

    def post(self, p):
        from datetime import datetime, timezone
        r = _s.post(f"{self.PDS}/com.atproto.server.createSession",
                    json={"identifier": _env(self.conf, "handle_env"),
                          "password": _env(self.conf, "password_env")}, timeout=30)
        sess = _check(r, "bluesky login")
        auth = {"Authorization": f"Bearer {sess['accessJwt']}"}
        blob = _check(_s.post(f"{self.PDS}/com.atproto.repo.uploadBlob", headers={**auth, "Content-Type": "image/png"},
                              data=Path(p["img_path"]).read_bytes(), timeout=60), "bluesky blob")["blob"]
        text = p["social"]
        if len(text) > 290:
            text = text[:287].rsplit(" ", 1)[0] + "…"
        record = {"$type": "app.bsky.feed.post", "text": text, "langs": [self.lang],
                  "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                  "embed": {"$type": "app.bsky.embed.external",
                            "external": {"uri": p["url"], "title": p["title"], "description": p["dek"],
                                         "thumb": blob}}}
        r = _s.post(f"{self.PDS}/com.atproto.repo.createRecord", headers=auth,
                    json={"repo": sess["did"], "collection": "app.bsky.feed.post", "record": record}, timeout=30)
        return _check(r, "bluesky post")["uri"]


CHANNELS = {c.name: c for c in (Telegram, Viber, Facebook, Instagram, Threads, Bluesky)}
