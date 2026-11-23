"""Тексти інтерфейсу сайтів."""

UI = {
    "uk": {
        "latest": "Останні новини", "read_more": "Читати", "source": "Джерело",
        "why": "Чому це важливо", "about": "Про видання", "privacy": "Конфіденційність",
        "older": "Старіші", "newer": "Новіші", "page": "Сторінка", "home": "Головна",
        "ai_note": "Матеріал підготовлено редакцією з використанням ШІ на основі публікації джерела. "
                   "Ми перевіряємо факти за першоджерелом і вказуємо посилання на нього.",
        "ymyl_note": "Матеріал має інформаційний характер і не є медичною чи фінансовою порадою.",
        "related": "Ще за темою", "notfound": "Сторінку не знайдено", "rss": "RSS",
        "about_text": "{name} — {tagline} Ми щодня відбираємо головні новини з перевірених джерел, "
                      "пояснюємо їх простою мовою і завжди даємо посилання на першоджерело. "
                      "Тексти готуються з використанням інструментів штучного інтелекту під контролем редакції.",
        "privacy_text": "Сайт використовує анонімну аналітику відвідувань і може показувати рекламу від Google. "
                        "Google та партнери можуть використовувати cookie для показу реклами. "
                        "Ми не збираємо персональних даних через форми. Керувати рекламними cookie можна "
                        "в налаштуваннях реклами Google.",
        "contact": "Зв'язок",
    },
    "en": {
        "latest": "Latest news", "read_more": "Read", "source": "Source",
        "why": "Why it matters", "about": "About", "privacy": "Privacy",
        "older": "Older", "newer": "Newer", "page": "Page", "home": "Home",
        "ai_note": "This story was prepared by our editors with the help of AI, based on the original report. "
                   "We check facts against the primary source and always link to it.",
        "ymyl_note": "This article is for information only and is not medical or financial advice.",
        "related": "More on this", "notfound": "Page not found", "rss": "RSS",
        "about_text": "{name} — {tagline} Every day we pick the key stories from trusted sources, "
                      "explain them in plain language and always link to the original. "
                      "Articles are prepared with AI tools under editorial oversight.",
        "privacy_text": "This site uses anonymous visit analytics and may show ads by Google. "
                        "Google and its partners may use cookies to serve ads. We do not collect personal "
                        "data through forms. You can manage ad cookies in Google Ads Settings.",
        "contact": "Contact",
    },
    "pl": {
        "latest": "Najnowsze", "read_more": "Czytaj", "source": "Źródło",
        "why": "Dlaczego to ważne", "about": "O nas", "privacy": "Prywatność",
        "older": "Starsze", "newer": "Nowsze", "page": "Strona", "home": "Strona główna",
        "ai_note": "Materiał przygotowała redakcja z pomocą AI na podstawie publikacji źródłowej. "
                   "Sprawdzamy fakty w źródle i zawsze podajemy link.",
        "ymyl_note": "Materiał ma charakter informacyjny i nie stanowi porady medycznej ani finansowej.",
        "related": "Więcej na ten temat", "notfound": "Nie znaleziono strony", "rss": "RSS",
        "about_text": "{name} — {tagline} Codziennie wybieramy najważniejsze wiadomości z zaufanych źródeł, "
                      "wyjaśniamy je prostym językiem i zawsze linkujemy do oryginału. "
                      "Teksty powstają z pomocą narzędzi AI pod nadzorem redakcji.",
        "privacy_text": "Strona korzysta z anonimowej analityki i może wyświetlać reklamy Google. "
                        "Google i partnerzy mogą używać plików cookie. Nie zbieramy danych osobowych przez "
                        "formularze. Ustawieniami reklam zarządzasz w Ustawieniach reklam Google.",
        "contact": "Kontakt",
    },
}


def t(lang: str) -> dict:
    return UI.get(lang, UI["en"])
