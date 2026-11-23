"""Генерація статичного сайту: сторінки, рубрики, sitemap, news-sitemap, RSS, robots, обкладинки."""
from __future__ import annotations

import json
import shutil
import time
from email.utils import formatdate
from pathlib import Path
from xml.sax.saxutils import escape

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .cards import make_card
from .common import CONTENT_DIR, LANG_NAMES, brand, OUT_DIR, STATIC_DIR, TEMPLATES_DIR, log, read_json, site_url
from .i18n import t

PER_PAGE = 24
_env = None


def env() -> Environment:
    global _env
    if _env is None:
        _env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))
        _env.filters["date"] = lambda ts, lang="uk": time.strftime("%d.%m.%Y, %H:%M", time.gmtime(ts + 7200))
        _env.filters["iso"] = lambda ts: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))
    return _env


def load_articles(site_id: str) -> list[dict]:
    arts = [read_json(f, None) for f in (CONTENT_DIR / site_id).glob("*.json")]
    arts = [a for a in arts if a]
    arts.sort(key=lambda a: -a["created"])
    return arts


def prefix(cfg: dict, lang: str) -> str:
    return "/" if lang == cfg["default_lang"] else f"/{lang}/"


def art_path(cfg: dict, lang: str, art: dict) -> str:
    return f"{prefix(cfg, lang)}{art['langs'][lang]['slug']}-{art['id'][-6:]}/"


def cat_label(cfg: dict, cat: str, lang: str) -> str:
    return cfg.get("category_labels", {}).get(cat, {}).get(lang, cat)


def _write(out: Path, rel: str, html: str) -> None:
    p = out / rel.lstrip("/")
    if rel.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")


def build_site(cfg: dict) -> Path:
    out = OUT_DIR / cfg["id"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    base = site_url(cfg)
    arts = load_articles(cfg["id"])
    log(f"[{cfg['id']}] збірка: {len(arts)} статей → {base}")

    shutil.copy(STATIC_DIR / "style.css", out / "style.css")
    (out / "img").mkdir()

    tpl = env()
    sitemap_urls: list[tuple[str, int, dict]] = []

    for lang in cfg["langs"]:
        ui = t(lang)
        la = [a for a in arts if lang in a["langs"]]
        common = {
            "cfg": cfg, "lang": lang, "ui": ui, "brand": brand(cfg, lang), "base": base, "pre": prefix(cfg, lang),
            "langs": cfg["langs"], "lang_names": LANG_NAMES,
            "tagline": cfg["tagline"].get(lang, ""), "year": time.gmtime().tm_year,
            "cats": [(c, cat_label(cfg, c, lang)) for c in cfg.get("categories", [])],
        }

        def card(a, _lang=lang):
            key = f"{a['id']}-{_lang}"
            src = make_card(cfg, a["langs"][_lang]["card_title"], cat_label(cfg, a["category"], _lang), key,
                            brand(cfg, _lang))
            dst = out / "img" / f"{key}.png"
            if not dst.exists():
                shutil.copy(src, dst)
            return f"/img/{key}.png"

        items = [{
            "a": a, "v": a["langs"][lang], "url": art_path(cfg, lang, a), "img": card(a),
            "cat": cat_label(cfg, a["category"], lang),
        } for a in la]

        # головна + пагінація
        pages = max(1, -(-len(items) // PER_PAGE))
        for p in range(1, pages + 1):
            chunk = items[(p - 1) * PER_PAGE:p * PER_PAGE]
            rel = common["pre"] if p == 1 else f"{common['pre']}page/{p}/"
            alts = {l: (prefix(cfg, l) if p == 1 else None) for l in cfg["langs"]}
            _write(out, rel, tpl.get_template("index.html").render(
                **common, items=chunk, page=p, pages=pages, canonical=base + rel,
                alternates={l: base + u for l, u in alts.items() if u}, title=None, heading=None))
            sitemap_urls.append((rel, int(time.time()), {}))

        # рубрики
        for c, label in common["cats"]:
            ci = [i for i in items if i["a"]["category"] == c][:60]
            if not ci:
                continue
            rel = f"{common['pre']}c/{c}/"
            _write(out, rel, tpl.get_template("index.html").render(
                **common, items=ci, page=1, pages=1, canonical=base + rel,
                alternates={l: base + f"{prefix(cfg, l)}c/{c}/" for l in cfg["langs"]},
                title=label, heading=label))

        # статті
        for n, it in enumerate(items):
            a = it["a"]
            alternates = {l: base + art_path(cfg, l, a) for l in a["langs"] if l in cfg["langs"]}
            related = [i for i in items if i["a"]["category"] == a["category"] and i is not it][:4]
            jsonld = {
                "@context": "https://schema.org", "@type": "NewsArticle",
                "headline": it["v"]["title"][:110], "description": it["v"]["dek"],
                "image": [base + it["img"]], "inLanguage": lang,
                "datePublished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(a["created"])),
                "dateModified": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(a["created"])),
                "author": {"@type": "Organization", "name": common["brand"], "url": base},
                "publisher": {"@type": "Organization", "name": common["brand"], "url": base},
                "mainEntityOfPage": base + it["url"],
                "isBasedOn": a["source"]["link"],
            }
            _write(out, it["url"], tpl.get_template("article.html").render(
                **common, it=it, related=related, canonical=base + it["url"], alternates=alternates,
                title=it["v"]["title"], jsonld=json.dumps(jsonld, ensure_ascii=False)))
            sitemap_urls.append((it["url"], a["created"], {"lang": lang, "title": it["v"]["title"],
                                                           "alternates": alternates}))

        # про нас / конфіденційність
        for slug, key in (("about", "about_text"), ("privacy", "privacy_text")):
            rel = f"{common['pre']}{slug}/"
            body = ui[key].format(name=common["brand"], tagline=common["tagline"])
            _write(out, rel, tpl.get_template("page.html").render(
                **common, title=ui[slug if slug == "about" else "privacy"], body=body,
                canonical=base + rel, alternates={l: base + f"{prefix(cfg, l)}{slug}/" for l in cfg["langs"]}))

        # RSS
        rss_items = "".join(
            f"<item><title>{escape(i['v']['title'])}</title><link>{base}{i['url']}</link>"
            f"<guid>{base}{i['url']}</guid><pubDate>{formatdate(i['a']['created'])}</pubDate>"
            f"<description>{escape(i['v']['dek'])}</description>"
            f"<enclosure url=\"{base}{i['img']}\" type=\"image/png\" length=\"0\"/></item>"
            for i in items[:50])
        (out / common["pre"].lstrip("/")).mkdir(parents=True, exist_ok=True)
        (out / common["pre"].lstrip("/") / "feed.xml").write_text(
            f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{escape(common['brand'])}</title><link>{base}{common['pre']}</link>"
            f"<description>{escape(common['tagline'])}</description><language>{lang}</language>"
            f"{rss_items}</channel></rss>", encoding="utf-8")

    # 404
    ui = t(cfg["default_lang"])
    (out / "404.html").write_text(tpl.get_template("page.html").render(
        cfg=cfg, lang=cfg["default_lang"], ui=ui, brand=brand(cfg, cfg["default_lang"]), base=base, pre="/", langs=cfg["langs"], lang_names=LANG_NAMES,
        tagline=cfg["tagline"].get(cfg["default_lang"], ""), year=time.gmtime().tm_year,
        cats=[(c, cat_label(cfg, c, cfg["default_lang"])) for c in cfg.get("categories", [])],
        title=ui["notfound"], body="", canonical=base + "/", alternates={}), encoding="utf-8")

    _sitemaps(cfg, out, base, sitemap_urls)
    (out / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\nSitemap: {base}/news-sitemap.xml\n")
    (out / "_headers").write_text(
        "/img/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/style.css\n  Cache-Control: public, max-age=3600\n")
    if cfg.get("ads_txt"):
        (out / "ads.txt").write_text(cfg["ads_txt"].strip() + "\n")
    return out


def _sitemaps(cfg, out: Path, base: str, urls) -> None:
    rows = []
    for rel, ts, meta in urls:
        alt = "".join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{u}"/>'
                      for l, u in meta.get("alternates", {}).items())
        rows.append(f"<url><loc>{base}{rel}</loc><lastmod>{time.strftime('%Y-%m-%d', time.gmtime(ts))}</lastmod>"
                    f"{alt}</url>")
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(rows) + "</urlset>", encoding="utf-8")
    cutoff = time.time() - 48 * 3600
    news = "".join(
        f"<url><loc>{base}{rel}</loc><news:news><news:publication><news:name>{escape(brand(cfg, meta['lang']))}</news:name>"
        f"<news:language>{meta['lang']}</news:language></news:publication>"
        f"<news:publication_date>{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(ts))}</news:publication_date>"
        f"<news:title>{escape(meta['title'])}</news:title></news:news></url>"
        for rel, ts, meta in urls if meta and ts >= cutoff)
    (out / "news-sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
        'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + news + "</urlset>", encoding="utf-8")
