"""Ілюстрації статей: одна на статтю для всіх мов.

1) ШІ-ілюстрація через Cloudflare Workers AI (flux-1-schnell, безкоштовний денний ліміт).
   Secrets: CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_AI_TOKEN (токен з правом Workers AI: Read).
2) Якщо ШІ недоступний/ліміт — фірмова картка сайту (без заголовка, щоб підходила всім мовам).

Нові картинки лежать у .cache/newimg/<site>/<id>.jpg; деплой заливає їх на VPS у /img/ і прибирає.
"""
from __future__ import annotations

import base64
import io
import os
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont

from .common import ROOT, STATIC_DIR, log

NEW_IMG = ROOT / ".cache" / "newimg"
W, H = 1200, 675
STYLE = ("Editorial paper collage illustration, cut-out paper shapes, halftone texture, muted palette with one "
         "accent color {accent}, clean light background, symbolic, modern magazine style, no text, no letters, "
         "no logos, no watermark. Scene: ")
FLUX = "https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/flux-1-schnell"


class _AI:
    """Один клієнт на процес; після ліміту/відмови авторизації в цьому прогоні API більше не смикаємо."""
    disabled = False
    session = requests.Session()


def _font(size: int):
    return ImageFont.truetype(str(STATIC_DIR / "fonts" / "Inter-Bold.otf"), size)


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _fit(img: Image.Image) -> Image.Image:
    """Обрізаємо до 16:9 і масштабуємо до 1200x675."""
    w, h = img.size
    target = W / H
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((W, H), Image.LANCZOS)


def ai_image(cfg: dict, prompt: str) -> Image.Image | None:
    acc, tok = os.environ.get("CLOUDFLARE_ACCOUNT_ID"), os.environ.get("CLOUDFLARE_AI_TOKEN")
    if _AI.disabled or not (acc and tok and prompt):
        return None
    full = STYLE.format(accent=cfg["colors"]["accent"]) + prompt
    try:
        r = _AI.session.post(FLUX.format(acc=acc), headers={"Authorization": f"Bearer {tok}"},
                             json={"prompt": full[:2000], "steps": 6}, timeout=90)
    except requests.RequestException as e:
        log(f"  ілюстрація: мережа {e}")
        return None
    if r.status_code in (401, 403, 429):
        log(f"  ілюстрація: Workers AI {r.status_code} — до кінця прогону без ШІ-картинок")
        _AI.disabled = True
        return None
    if r.status_code != 200:
        log(f"  ілюстрація: HTTP {r.status_code} {r.text[:200]}")
        return None
    b64 = (r.json().get("result") or {}).get("image")
    if not b64:
        log(f"  ілюстрація: порожня відповідь {r.text[:200]}")
        return None
    return _fit(Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB"))


def brand_card(cfg: dict, label: str) -> Image.Image:
    """Запасна картинка: фірмовий фон + назва видання + рубрика латиницею."""
    bg, accent = _hex(cfg["colors"]["card_bg"]), _hex(cfg["colors"]["accent"])
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    for i, (x, y, r) in enumerate(((980, 120, 260), (1120, 560, 180), (760, 600, 90))):
        k = 0.35 - i * 0.08
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(bg[j] + (accent[j] - bg[j]) * k) for j in range(3)))
    d.rectangle([0, 0, 14, H], fill=accent)
    d.text((80, H // 2 - 70), cfg.get("name_latin") or cfg["name"], font=_font(96), fill=(255, 255, 255))
    d.text((84, H // 2 + 50), label.upper(), font=_font(34), fill=accent)
    return img


def make_image(cfg: dict, art: dict) -> str:
    """Генерує картинку статті → /img/<id>.jpg; ставить art['image_ai'] (чи це ШІ-ілюстрація)."""
    img = ai_image(cfg, art.get("image_prompt", ""))
    art["image_ai"] = img is not None
    if img is None:
        label = cfg.get("category_labels", {}).get(art["category"], {}).get("en", art["category"])
        img = brand_card(cfg, label)
    out = NEW_IMG / cfg["id"] / f"{art['id']}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return f"/img/{art['id']}.jpg"


def local_image(cfg: dict, art: dict) -> Path | None:
    p = NEW_IMG / cfg["id"] / f"{art['id']}.jpg"
    return p if p.exists() else None
