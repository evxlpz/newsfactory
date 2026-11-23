"""Деплой зібраних сайтів у Cloudflare Pages (direct upload через wrangler).

Потрібні Secrets: CLOUDFLARE_API_TOKEN (права Pages:Edit), CLOUDFLARE_ACCOUNT_ID.
Проєкт Pages створюється автоматично, якщо його ще нема.
"""
from __future__ import annotations

import os
import subprocess
import sys

from .common import OUT_DIR, load_sites, log


def sh(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def main() -> None:
    if not (os.environ.get("CLOUDFLARE_API_TOKEN") and os.environ.get("CLOUDFLARE_ACCOUNT_ID")):
        log("Cloudflare: немає CLOUDFLARE_API_TOKEN / CLOUDFLARE_ACCOUNT_ID — деплой пропущено")
        return
    failed = []
    for cfg in load_sites():
        proj = cfg["pages_project"]
        out = OUT_DIR / cfg["id"]
        if not out.exists():
            continue
        r = sh(["npx", "--yes", "wrangler@4", "pages", "project", "create", proj, "--production-branch", "main"])
        if r.returncode == 0:
            log(f"[{cfg['id']}] створено Pages-проєкт {proj}")
        r = sh(["npx", "--yes", "wrangler@4", "pages", "deploy", str(out), "--project-name", proj,
                "--branch", "main", "--commit-dirty=true"])
        if r.returncode != 0:
            log(f"[{cfg['id']}] деплой ✗\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
            failed.append(cfg["id"])
        else:
            url = next((ln for ln in r.stdout.splitlines() if "pages.dev" in ln), "").strip()
            log(f"[{cfg['id']}] деплой ✓ {url}")
    if failed:
        sys.exit(f"деплой не вдався: {', '.join(failed)}")


if __name__ == "__main__":
    main()
