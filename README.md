# newsfactory

5 AI-новинних сайтів на одному рушії: **Нейрон** (ШІ/техно), **Капітал** (гроші/крипта),
**Пульс** (здоров'я), **Стрічка** (новини UA), **Дивосвіт** (цікаве).

## Secrets (Settings → Secrets and variables → Actions)

Обов'язкові:
| Secret | Що це |
|---|---|
| `GEMINI_API_KEY` | ключ Gemini (можна додати `GEMINI_API_KEY_2`, `_3`… — рушій їх ротує) |
| `CLOUDFLARE_API_TOKEN` | токен з правом **Cloudflare Pages: Edit** |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID з дашборду Cloudflare |

Алерти й звіти:
| `TG_BOT_TOKEN` | бот, який постить у канали й шле алерти |
| `ADMIN_TG_CHAT` | твій chat id для алертів/звітів |

Соцмережі (по кожному сайту, суфікс = AITECH / MONEY / HEALTH / NEWSUA / LIFESTYLE):
`TG_CHAT_*`, `VIBER_TOKEN_*` + `VIBER_FROM_*`, `FB_PAGE_ID_*` + `FB_TOKEN_*`, `IG_USER_ID_*`,
`THREADS_USER_ID_*` + `THREADS_TOKEN_*`, `BSKY_HANDLE_*` + `BSKY_PASSWORD_*` (app password).
Канал вмикається сам, щойно з'являються його Secrets.

## Запуск вручну
Actions → newsfactory → Run workflow (можна вказати сайти або «тільки збірка»).
