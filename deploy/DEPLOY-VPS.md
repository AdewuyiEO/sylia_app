# Deploy Sylia on one VPS

Everything runs on one server: HTTPS (Caddy), the API, a background worker
(try-on, garment tagging), Postgres, Redis, and nightly database backups.
Photos are stored on the server's disk. About 20 minutes the first time.

## What you need
- A VPS: Ubuntu 24.04, **2 vCPU / 4 GB RAM / 40 GB+ disk** (Hetzner, DigitalOcean,
  Contabo, …). Turn on the provider's **automatic backups** when you create it —
  that is the copy of your photos and database that survives if the server dies.
- A domain (or subdomain) for the API, e.g. `api.sylia.app`.

## 1. SSH key (once, on your Windows PC, in PowerShell)
```powershell
ssh-keygen -t ed25519
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```
Paste that public key into the VPS provider when you create the server.

## 2. DNS
At your domain registrar add an **A record**: `api` → your server's IP address.

## 3. Install (on the server)
```powershell
ssh root@YOUR_SERVER_IP
```
then on the server:
```bash
git clone https://github.com/AdewuyiEO/sylia_app.git sylia
cd sylia/deploy
bash setup-server.sh api.yourdomain.com
nano .env                     # paste ANTHROPIC_API_KEY etc. Ctrl+O, Enter, Ctrl+X
docker compose up -d --build
```
Open `https://api.yourdomain.com/health` — it should say `"status":"ok"`.

## Everyday commands (in `sylia/deploy`)
| Task | Command |
|---|---|
| Update to the latest code | `git pull && docker compose up -d --build` |
| See what's running | `docker compose ps` |
| Live logs | `docker compose logs -f api worker` |
| Restart everything | `docker compose restart` |
| List database backups | `docker compose exec backup ls -lh /backups` |
| Disk space | `df -h` |

## Restore the database from a backup
```bash
docker compose stop api worker
docker compose exec -T backup sh -c 'gunzip -c /backups/sylia-YYYYMMDD-HHMM.sql.gz | psql -h db -U sylia -d sylia'
docker compose start api worker
```

## Good to know
- Secrets live in `deploy/.env` on the server only (never in git).
- Only ports 22, 80 and 443 are open; Postgres and Redis are internal.
- Security updates install automatically; reboot now and then (`reboot`).
- Database backups sit on the same disk; the provider's server backups are what
  protect you from losing the whole machine. For an extra off-server copy later,
  add a storage box and copy `/var/lib/docker/volumes/sylia_backups` to it.
- Growing: resize the VPS in the provider panel (minutes), or later move photos to
  object storage with `STORAGE_BACKEND=s3` — the app doesn't change.
