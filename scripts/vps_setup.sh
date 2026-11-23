#!/usr/bin/env bash
# Ідемпотентне налаштування VPS (Ubuntu/Debian): Caddy + папка сайтів + файрвол.
# Запускається автоматично з GitHub Actions перед кожним деплоєм — повторний запуск нічого не ламає.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

if ! command -v caddy >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl gnupg rsync
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -qq
  apt-get install -y -qq caddy
  systemctl enable --now caddy
fi
command -v rsync >/dev/null 2>&1 || apt-get install -y -qq rsync

mkdir -p /srv/sites
chmod 755 /srv /srv/sites

if command -v ufw >/dev/null 2>&1 && ! ufw status | grep -q "Status: active"; then
  ufw allow OpenSSH >/dev/null
  ufw allow 80/tcp >/dev/null
  ufw allow 443/tcp >/dev/null
  ufw --force enable >/dev/null
fi
echo "vps ok"
