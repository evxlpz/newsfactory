# newsfactory

5 AI-новинних сайтів на одному рушії: **Нейрон** (ШІ/техно), **Капітал** (гроші/крипта),
**Пульс** (здоров'я, тільки UA/EN), **Стрічка** (новини UA), **Дивосвіт** (цікаве). Решта сайтів — 13 мов.

Хостинг — свій VPS (Hetzner) з Caddy: без лімітів на кількість файлів, HTTPS автоматичний.
Поки нема доменів, сайти живуть на `<subdomain>.<ip-через-дефіси>.sslip.io`.

## Разове налаштування

1. **VPS Hetzner**: Ubuntu 24.04, найменший тариф. На компі створи ключ:
   `ssh-keygen -t ed25519 -f newsfactory -N ""` → вміст `newsfactory.pub` додай у Hetzner при створенні сервера,
   вміст `newsfactory` (приватний) — у Secret `VPS_SSH_KEY`, IP сервера — у `VPS_HOST`.
   Caddy й усе інше рушій поставить сам при першому деплої.
2. **Gemini**: `GEMINI_API_KEY` (+ `_2`, `_3`… — ліміт рахується на проєкт/акаунт, рушій перемикається сам).
3. **ШІ-ілюстрації** (Cloudflare Workers AI, безкоштовний денний ліміт): `CLOUDFLARE_ACCOUNT_ID`,
   `CLOUDFLARE_AI_TOKEN` (API Token з правом *Workers AI: Read*). Без них — фірмові картки замість ілюстрацій.
4. **Telegram**: `TG_BOT_TOKEN` (бот — адмін у каналах), `ADMIN_TG_CHAT` (твій chat id для алертів/звітів).

Соцмережі (суфікс = AITECH / MONEY / HEALTH / NEWSUA / LIFESTYLE):
`TG_CHAT_*`, `VIBER_TOKEN_*` + `VIBER_FROM_*`, `FB_PAGE_ID_*` + `FB_TOKEN_*`, `IG_USER_ID_*`,
`THREADS_USER_ID_*` + `THREADS_TOKEN_*`, `BSKY_HANDLE_*` + `BSKY_PASSWORD_*`.
Канал вмикається сам, щойно з'являються його Secrets.

## Запуск вручну
Actions → newsfactory → Run workflow.

## Свій домен
Вписати `domain: example.com` у `sites/<id>/site.yaml`, A-запис домену → IP VPS. Старий sslip-адрес сам редіректить.
