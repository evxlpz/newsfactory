"""Переписування новини своїми словами під усі мови сайту одним запитом до Gemini."""
from __future__ import annotations

import time

import nh3

from .common import CONTENT_DIR, LANG_NAMES, sha, slugify, write_json

ALLOWED_TAGS = {"p", "h2", "h3", "ul", "ol", "li", "strong", "em", "blockquote", "a", "br"}

UK_STYLE = """Правила української (обов'язково для мови uk):
- сучасний правопис 2019, жива літературна мова, без русизмів і кальок:
  «брати участь» (не «приймати участь»), «протягом» (не «на протязі»), «наступний» (не «слідуючий»),
  «є» (не «являється»), «через» (не «у зв'язку з»), «вживати заходів» (не «приймати міри»),
  «відповідно до» (не «згідно з» у кожному реченні), «найкращий» (не «самий кращий»);
- штучний інтелект = «ШІ» (не «AI»/«ІІ»); лапки «ялинки»; апостроф ’;
- тисячі через пробіл (10 000), валюта: 100 грн, $100, €100;
- назви компаній і продуктів латиницею як в оригіналі (OpenAI, Google, iPhone).
"""


def _prompt(cfg: dict, item: dict, fulltext: str) -> str:
    langs = cfg["langs"]
    lang_list = ", ".join(f"{l} ({LANG_NAMES.get(l, l)})" for l in langs)
    cats = ", ".join(cfg.get("categories", ["news"]))
    ymyl = ""
    if cfg.get("ymyl"):
        ymyl = ("\nЦе YMYL-тематика (здоров'я/гроші). НІЯКИХ порад що купувати, як лікуватись, у що інвестувати. "
                "Тільки факти з джерела. Якщо в джерелі дослідження — вкажи, що це дослідження, на кому/чому і що "
                "висновки попередні, якщо так і є. Не перебільшуй.\n")
    source_text = fulltext or item["summary"]
    return f"""Ти — редактор видання «{cfg['name']}». Тематика: {cfg['topic']}.
{cfg.get('editorial', '')}
{ymyl}
Завдання: на основі новини нижче напиши ОРИГІНАЛЬНИЙ матеріал (не переклад і не перефраз речення-в-речення) мовами: {lang_list}.
Кожна мова — окремий текст, написаний природно для носія цієї мови, а не машинний переклад.

Правила:
- тільки факти з джерела, нічого не вигадуй (цифри, цитати, дати, імена — лише ті, що є);
- додай короткий контекст «чому це важливо» для читача;
- не копіюй речення з джерела; цитати — максимум одна коротка, в лапках;
- без клікбейту, без емодзі в заголовку, без «шокуюча новина»;
- body_html: 250–450 слів, теги лише <p>, <h2>, <ul>, <li>, <strong>, <blockquote>; без посилань;
- social: 1–3 речення для соцмереж + 2–3 хештеги, мовою відповідної версії;
- card_title: до 70 символів, для картинки-обкладинки.
{UK_STYLE}
Постав skip=true, якщо: це реклама/прес-реліз без новини, дубль, тема не відповідає тематиці сайту,
або в джерелі замало фактів для нормального тексту.
Категорія — одна з: {cats}.

Поверни тільки JSON:
{{"skip": false, "skip_reason": "", "category": "...",
  "langs": {{"<код мови>": {{"title": "...", "dek": "1-2 речення ліду", "body_html": "...",
     "why": "1-2 речення", "tags": ["...", "..."], "social": "...", "card_title": "..."}}}}}}

ДЖЕРЕЛО: {item['source']}
ЗАГОЛОВОК: {item['title']}
ТЕКСТ:
{source_text}
"""


def _sanitize(html_text: str) -> str:
    return nh3.clean(html_text, tags=ALLOWED_TAGS, attributes={"a": {"href"}}, link_rel="nofollow noopener")


def rewrite(cfg: dict, item: dict, fulltext: str, gemini) -> dict | None:
    data = gemini.json(_prompt(cfg, item, fulltext))
    if data.get("skip"):
        return {"skip": True, "reason": data.get("skip_reason", "")}
    langs_out = {}
    for lang in cfg["langs"]:
        v = (data.get("langs") or {}).get(lang)
        if not v or not v.get("title") or len(v.get("body_html", "")) < 600:
            continue
        v["body_html"] = _sanitize(v["body_html"])
        v["title"] = v["title"].strip().rstrip(".")
        v["card_title"] = (v.get("card_title") or v["title"])[:90]
        v["slug"] = slugify(v["title"])
        v["tags"] = [t.strip().lstrip("#") for t in v.get("tags", []) if t.strip()][:6]
        langs_out[lang] = v
    if cfg["default_lang"] not in langs_out:
        return {"skip": True, "reason": "немає основної мови в відповіді"}
    cats = cfg.get("categories", ["news"])
    art = {
        "id": time.strftime("%Y%m%d%H%M") + "-" + sha(item["link"])[:6],
        "created": int(time.time()),
        "category": data.get("category") if data.get("category") in cats else cats[0],
        "source": {"name": item["source"], "title": item["title"], "link": item["link"]},
        "langs": langs_out,
    }
    write_json(CONTENT_DIR / cfg["id"] / f"{art['id']}.json", art)
    return art
