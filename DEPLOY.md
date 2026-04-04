# DEPLOY.md — MapsProveFiber Production Deployment Guide

## Requirements

| Tool | Minimum version |
|------|----------------|
| Docker | 24.x |
| Docker Compose | v2.20 |
| Linux server | Ubuntu 22.04+ / Debian 12+ |
| Open ports | 80, 443 |
| RAM | 2 GB (4 GB recommended) |
| Disk | 10 GB free |

---

## Quick Start (single server, HTTPS)

```bash
# 1. Clone the repository (or pull the pre-built image from GHCR)
git clone https://github.com/kaled182/provemaps_beta.git
cd provemaps_beta

# 2. Configure environment
cp .env.production.example .env.production
nano .env.production          # fill in all required values

# 3. Deploy (profile: minimal — web + postgres + redis + nginx + celery)
./scripts/deploy.sh --profile minimal --init-data

# 4. Open the application
open https://<DOMAIN_NAME>
```

---

## .env.production Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key (50+ random chars) | `openssl rand -base64 50` |
| `DB_PASSWORD` | PostgreSQL password | strong password |
| `REDIS_PASSWORD` | Redis password | strong password |
| `DOMAIN_NAME` | Your domain (no https://) | `app.example.com` |
| `CERTBOT_EMAIL` | Let's Encrypt contact email | `you@example.com` |
| `ALLOWED_HOSTS` | Comma-separated host list | `app.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Comma-separated origins | `https://app.example.com` |
| `ADMIN_USERNAME` | Initial superuser username | `admin` |
| `ADMIN_PASSWORD` | Initial superuser password | strong password |
| `ADMIN_EMAIL` | Initial superuser email | `admin@example.com` |

Generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## Docker Compose Profiles

Select the set of services to run via `COMPOSE_PROFILES` in `.env.production`
or the `--profile` flag to `deploy.sh`.

| Profile | Services included |
|---------|-------------------|
| `minimal` | web, celery, celery-beat, postgres, redis, nginx, certbot |
| `monitoring` | + Prometheus, Grafana |
| `video` | + MediaMTX (RTMP/RTSP/WebRTC) |
| `whatsapp` | + WhatsApp QR service |
| `full` | All of the above |

```bash
# Example: start with monitoring enabled
./scripts/deploy.sh --profile monitoring
```

---

## SSL Certificate (Let's Encrypt)

`deploy.sh` handles the bootstrap automatically on first run.

**How it works:**

1. Starts nginx with `nginx.initial.conf` (HTTP-only, port 80)
2. Runs `certbot certonly --webroot` to obtain the certificate
3. Restarts nginx with `nginx.prod.conf` (HTTPS, Let's Encrypt paths)
4. The `certbot` container renews automatically every 12 hours

**Manual renewal:**

```bash
docker compose -f docker/docker-compose.prod.yml exec certbot \
  certbot renew --webroot -w /var/www/certbot
docker compose -f docker/docker-compose.prod.yml exec nginx nginx -s reload
```

**Skip certbot (self-signed / existing cert):**

```bash
./scripts/deploy.sh --no-certbot
```

Then place your own certificate at:
- `/etc/letsencrypt/live/<DOMAIN>/fullchain.pem`
- `/etc/letsencrypt/live/<DOMAIN>/privkey.pem`

inside the `letsencrypt` Docker volume.

---

## Initial Data

To create the default superuser and register Celery periodic tasks:

```bash
# Included automatically when using --init-data flag:
./scripts/deploy.sh --init-data

# Or run manually after deploy:
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py init_app_data
```

Credentials come from `.env.production`:
`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_EMAIL`

---

## Backup

```bash
# Full backup (postgres + redis), keep last 7
./scripts/backup.sh

# Custom output directory and retention
./scripts/backup.sh --output-dir /mnt/backups --retention 30

# PostgreSQL only
./scripts/backup.sh --no-redis
```

Backups are stored in `BACKUP_DIR` (default `/backups`):
```
/backups/
  postgres/  pg_<dbname>_<timestamp>.sql.gz
  redis/     redis_<timestamp>.rdb
```

**Restore PostgreSQL:**

```bash
gunzip -c /backups/postgres/pg_mapsprovefiber_<timestamp>.sql.gz | \
  docker compose -f docker/docker-compose.prod.yml exec -T postgres \
    psql -U mapsprovefiber mapsprovefiber
```

---

## Monitoring (optional profile)

After starting with `--profile monitoring`:

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | `http://<host>:3002` | admin / `GF_SECURITY_ADMIN_PASSWORD` |
| Prometheus | `http://<host>:9090` | (no auth by default) |

Both ports are bound to `127.0.0.1` — expose via SSH tunnel or additional nginx proxy.

---

## Updating to a New Version

```bash
# Pull latest image from GHCR
docker pull ghcr.io/kaled182/provemaps_beta:<version>

# Or rebuild from source
git pull
./scripts/deploy.sh
```

Deploy applies migrations automatically before restarting services.

---

## Logs

```bash
# All services
docker compose -f docker/docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker/docker-compose.prod.yml logs -f web

# Last 100 lines
docker compose -f docker/docker-compose.prod.yml logs --tail=100 web
```

Log rotation is configured per container: `max-size: 10m, max-file: 5`.

---

## Common Operations

```bash
# Stop all services
docker compose -f docker/docker-compose.prod.yml down

# Restart a single service
docker compose -f docker/docker-compose.prod.yml restart web

# Run a management command
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py <command>

# Open a Django shell
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py shell

# Open a database shell
docker compose -f docker/docker-compose.prod.yml exec postgres \
  psql -U mapsprovefiber mapsprovefiber
```

---

## Troubleshooting

### Health check fails

```bash
docker compose -f docker/docker-compose.prod.yml logs web
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py check --deploy
```

### Migrations pending

```bash
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py showmigrations | grep '\[ \]'
docker compose -f docker/docker-compose.prod.yml exec web \
  python manage.py migrate
```

### Redis authentication error

Verify `REDIS_PASSWORD` matches in `.env.production` and that `REDIS_URL`
follows the format `redis://:<password>@redis:6379/0`.

### SSL certificate not found

Run `./scripts/deploy.sh` again without `--no-certbot`, or check that
`DOMAIN_NAME` and `CERTBOT_EMAIL` are set correctly in `.env.production`.
