#!/usr/bin/env bash
# One-time setup for a fresh Ubuntu 24.04 VPS. Run as root from sylia/deploy:
#   bash setup-server.sh api.yourdomain.com
# Installs Docker, a firewall (SSH/HTTP/HTTPS only), automatic security updates,
# fail2ban and 2 GB swap, then writes .env with freshly generated secrets.
set -euo pipefail

DOMAIN="${1:-}"
if [ -z "$DOMAIN" ]; then
  echo "usage: bash setup-server.sh api.yourdomain.com" >&2
  exit 1
fi
cd "$(dirname "$0")"

echo "==> system updates"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get upgrade -y
apt-get install -y ca-certificates curl ufw fail2ban unattended-upgrades openssl

echo "==> automatic security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> firewall: SSH, HTTP, HTTPS only"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

echo "==> fail2ban (blocks repeated SSH login attempts)"
systemctl enable --now fail2ban

if ! swapon --show | grep -q .; then
  echo "==> 2 GB swap (headroom for try-on renders on small servers)"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

if ! command -v docker >/dev/null; then
  echo "==> Docker (official apt repository)"
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
# Docker publishes ports past ufw; only Caddy publishes any (80/443), everything else stays internal.

if [ ! -f .env ]; then
  echo "==> .env with generated secrets"
  rand() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-"$1"; }
  sed -e "s|^DOMAIN=.*|DOMAIN=${DOMAIN}|" \
      -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(rand 32)|" \
      -e "s|^JWT_SECRET=.*|JWT_SECRET=$(rand 48)|" \
      -e "s|^ENCRYPTION_KEY=.*|ENCRYPTION_KEY=$(rand 43)|" \
      -e "s|^ADMIN_TOKEN=.*|ADMIN_TOKEN=$(rand 40)|" \
      .env.example > .env
  chmod 600 .env
else
  echo "==> .env already exists — kept as is"
fi

echo
echo "Done. Next:"
echo "  1. nano .env      (paste ANTHROPIC_API_KEY and any other keys you have)"
echo "  2. docker compose up -d --build"
echo "  3. open https://${DOMAIN}/health"
