"""Деплой на свій VPS (Hetzner): rsync HTML + нові картинки, конфіг Caddy з автоматичним HTTPS.

Secrets: VPS_HOST (IP сервера), VPS_SSH_KEY (приватний ключ), VPS_USER (за замовчуванням root).
Без свого домену сайт живе на <subdomain>.<ip-через-дефіси>.sslip.io — HTTPS теж автоматичний.
Перший запуск сам ставить Caddy (scripts/vps_setup.sh).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

from .common import OUT_DIR, ROOT, load_sites, log, site_host
from .images import NEW_IMG

REMOTE = "/srv/sites"
SSH_OPTS = ["-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes"]


def _target() -> str:
    return f"{os.environ.get('VPS_USER', 'root')}@{os.environ['VPS_HOST']}"


def ssh(cmd: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["ssh", *SSH_OPTS, _target(), cmd], input=stdin, capture_output=True, text=True)


def rsync(src: str, dst: str, delete: bool, exclude: list[str] | None = None) -> subprocess.CompletedProcess:
    args = ["rsync", "-az", "--chmod=D755,F644", "-e", "ssh " + " ".join(SSH_OPTS)]
    if delete:
        args.append("--delete")
    for e in exclude or []:
        args += ["--exclude", e]
    return subprocess.run([*args, src, f"{_target()}:{dst}"], capture_output=True, text=True)


def caddyfile(sites: list[dict]) -> str:
    blocks = []
    for cfg in sites:
        host = site_host(cfg)
        blocks.append(f"""{host} {{
\troot * {REMOTE}/{cfg['id']}
\tencode zstd gzip
\t@img path /img/*
\theader @img Cache-Control "public, max-age=31536000, immutable"
\t@html path *.html */
\theader @html Cache-Control "public, max-age=120"
\tfile_server
\thandle_errors {{
\t\trewrite * /404.html
\t\tfile_server
\t}}
}}
""")
        if cfg.get("domain"):  # старий sslip-хост → редірект на домен (зберігаємо вагу посилань)
            ip = os.environ["VPS_HOST"].replace(".", "-")
            blocks.append(f"{cfg['subdomain']}.{ip}.sslip.io {{\n\tredir https://{host}{{uri}} permanent\n}}\n")
    return "\n".join(blocks)


def main() -> None:
    if not (os.environ.get("VPS_HOST") and os.environ.get("VPS_SSH_KEY")):
        log("VPS: немає VPS_HOST / VPS_SSH_KEY — деплой пропущено")
        return
    sites = load_sites()
    r = ssh("bash -s", (ROOT / "scripts" / "vps_setup.sh").read_text())
    if r.returncode != 0:
        sys.exit(f"VPS setup ✗\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}")
    failed = []
    for cfg in sites:
        out = OUT_DIR / cfg["id"]
        if not out.exists():
            continue
        r = rsync(f"{out}/", f"{REMOTE}/{cfg['id']}/", delete=True, exclude=["img/"])
        if r.returncode != 0:
            log(f"[{cfg['id']}] rsync html ✗ {r.stderr[-800:]}")
            failed.append(cfg["id"])
            continue
        new = NEW_IMG / cfg["id"]
        if new.exists() and any(new.iterdir()):
            r = rsync(f"{new}/", f"{REMOTE}/{cfg['id']}/img/", delete=False)
            if r.returncode != 0:
                log(f"[{cfg['id']}] rsync img ✗ {r.stderr[-800:]}")
                failed.append(cfg["id"])
                continue
            shutil.rmtree(new)  # залиті — локально більше не потрібні
        log(f"[{cfg['id']}] деплой ✓ https://{site_host(cfg)}")
    r = ssh("cat > /etc/caddy/Caddyfile.new && caddy validate --config /etc/caddy/Caddyfile.new --adapter caddyfile "
            "&& mv /etc/caddy/Caddyfile.new /etc/caddy/Caddyfile && systemctl reload caddy", caddyfile(sites))
    if r.returncode != 0:
        log(f"Caddy конфіг ✗ {r.stdout[-800:]} {r.stderr[-800:]}")
        failed.append("caddy")
    if failed:
        sys.exit(f"деплой не вдався: {', '.join(failed)}")


if __name__ == "__main__":
    main()
