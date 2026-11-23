"""Обкладинки статей 1200x630 (сайт, OG, соцмережі) — свої картинки, без чужих фото."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import ROOT, STATIC_DIR

CACHE = ROOT / ".cache" / "img"
W, H = 1200, 630
_fonts: dict = {}


def _font(kind: str, size: int):
    key = (kind, size)
    if key not in _fonts:
        name = "Inter-Bold.otf" if kind == "bold" else "Inter-Regular.otf"
        _fonts[key] = ImageFont.truetype(str(STATIC_DIR / "fonts" / name), size)
    return _fonts[key]


def _hex(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _wrap(draw, text: str, font, max_w: int, max_lines: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and " ".join(lines) != text:
        lines[-1] = lines[-1].rstrip(" ,.;:") + "…"
    return lines


def make_card(cfg: dict, title: str, label: str, key: str, name: str | None = None) -> Path:
    """Повертає шлях до PNG у кеші (генерує, якщо нема)."""
    path = CACHE / cfg["id"] / f"{key}.png"
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    bg = _hex(cfg["colors"]["card_bg"])
    accent = _hex(cfg["colors"]["accent"])
    fg = (255, 255, 255)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    pad = 72
    # смуга акценту зліва
    d.rectangle([0, 0, 14, H], fill=accent)
    # мітка рубрики
    lf = _font("bold", 26)
    label = label.upper()
    lw = d.textlength(label, font=lf)
    d.rounded_rectangle([pad, pad, pad + lw + 36, pad + 50], radius=8, fill=accent)
    d.text((pad + 18, pad + 10), label, font=lf, fill=bg)
    # заголовок: підбираємо розмір, щоб влазив
    for size in (64, 58, 52, 46):
        tf = _font("bold", size)
        lines = _wrap(d, title, tf, W - pad * 2, 4)
        if len(lines) <= 4 and not lines[-1].endswith("…"):
            break
    y = pad + 90
    for ln in lines:
        d.text((pad, y), ln, font=tf, fill=fg)
        y += int(size * 1.22)
    # назва сайту знизу
    nf = _font("bold", 30)
    d.text((pad, H - pad - 30), name or cfg["name"], font=nf, fill=accent)
    img.save(path, "PNG", optimize=True)
    return path
