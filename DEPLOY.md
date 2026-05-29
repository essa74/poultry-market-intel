# Production Deployment — Poultry Market Intel

## Prerequisites

- **VPS** running Ubuntu 22.04+ (or any Debian-based distro)
- **Docker** & **Docker Compose** plugin installed
- **Domain name** (e.g., `poultrymarketintel.com`) pointing to your VPS IP — optional for initial setup
- **Firewall**: ports `80` (HTTP) and `443` (HTTPS) open

## 1. Clone & prepare

```bash
git clone <repo-url> /opt/poultry-market-intel
cd /opt/poultry-market-intel
```

## 2. Environment setup

```bash
cp .env.production.example .env.production
```

Edit `.env.production` and set:

| Variable | Description | Required |
|----------|-------------|----------|
| `POSTGRES_PASSWORD` | Strong random password for the database | Yes |
| `ADMIN_TOKEN` | Token for admin API access — **backend won't start without it** | Yes |
| `ENV` | Must be `production` | Yes |
| `CORS_ORIGINS` | Comma-separated allowed origins (your domain) | Yes |
| `SCHEDULER_ENABLED` | `true` to enable auto-scraping scheduler | Yes |

> **Local dev only**: `backend/.env` uses `ADMIN_TOKEN=8191`.  
> **Production must use a strong token** — generate one with:

```bash
openssl rand -base64 32   # for POSTGRES_PASSWORD
openssl rand -base64 32   # for ADMIN_TOKEN
```

## 3. Deploy

```bash
./scripts/deploy.sh
```

This will:
1. Pull and build the Docker images (backend, web)
2. Run Alembic database migrations (`alembic upgrade head`)
3. Start all services (nginx, backend, web, PostgreSQL)
4. Clean up unused Docker images

### Manual migration (if needed)

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head
```

### Docker Compose (full stack)

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

## 4. Verify

```bash
# Service status
docker compose -f docker-compose.prod.yml --env-file .env.production ps

# Backend health
curl http://localhost:8000/health

# Scraper status (requires admin token)
curl -H "X-Admin-Token: YOUR_TOKEN" http://localhost:8000/api/v1/scraping/status
```

Visit `http://<your-domain>` in a browser.

## 5. Admin token usage

All write/debug API endpoints require the `ADMIN_TOKEN`. Send it as:

**HTTP Header:**
```
X-Admin-Token: your-token-here
```

**Authorization Bearer:**
```
Authorization: Bearer your-token-here
```

In the **Admin UI** (`/admin/scraping`), enter the token in the prompt at the top of the page. It will be stored in your browser's `localStorage`.

### Protected endpoints (require ADMIN_TOKEN)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/scraping/run` | Trigger full collection |
| POST | `/api/v1/scraping/sources/{id}/run` | Run single source |
| POST | `/api/v1/scraping/reset` | Reset all data |
| POST | `/api/v1/scraping/sources` | Create source |
| PATCH | `/api/v1/scraping/sources/{id}/toggle` | Toggle source |
| PATCH | `/api/v1/scraping/sources/{id}/post-urls` | Update source URLs |
| DELETE | `/api/v1/scraping/sources/{id}` | Delete source |
| POST | `/api/v1/prices/manual` | Manual price entry |
| POST/PUT/DELETE | `/api/v1/prices/*` | Price CRUD |
| GET | `*/facebook-debug`, `*/debug/*`, `*/ocr-preview` | Debug endpoints |

### Public endpoints (no token needed)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/prices/latest` | Latest prices |
| GET | `/api/v1/prices/trends` | Price trends |
| GET | `/api/v1/prices/` | List prices |
| GET | `/api/v1/prices/{id}` | Get single price |
| GET | `/api/v1/scraping/status` | Scraper status |
| GET | `/api/v1/scraping/sources` | List sources |
| GET | `/api/v1/scraping/logs` | List scraper logs |
| GET | `/api/v1/news/*` | News endpoints |
| GET | `/api/v1/predictions/*` | Prediction endpoints |
| GET | `/api/v1/holidays/*` | Holiday endpoints |

## 6. Database backups

### Linux / macOS

```bash
# Manual backup
./scripts/backup-db.sh

# Schedule daily (crontab)
# 0 2 * * * cd /opt/poultry-market-intel && ./scripts/backup-db.sh >> /var/log/poultry-backup.log 2>&1
```

### Windows

```cmd
# Manual backup
scripts\backup_postgres.bat

# Schedule daily (Task Scheduler)
# schtasks /create /tn "Poultry Backup" /tr "C:\poultry-market-intel\scripts\backup_postgres.bat" /daily /st 02:00
```

### Restore from backup

```bash
# From SQL dump (Linux)
gunzip -c backups/poultry_market_20260101_020000.sql.gz | docker exec -i poultry-market-intel-db-1 psql -U poultry -d poultry_market

# From SQL dump (Windows)
# type backups\poultry_market_20260101_020000.sql | docker exec -i poultry-market-intel-db-1 psql -U poultry -d poultry_market
```

Backups are stored in `./backups/`. The script keeps the last 14 daily backups.

## 7. Scheduler notes

The backend starts an internal **APScheduler** that runs:

| Job | Schedule | Description |
|-----|----------|-------------|
| Morning collection | `06:00` daily | Scrape all active sources |
| Evening collection | `18:00` daily | Scrape all active sources |
| Facebook auto-discover | Every 3 hours | Auto-discover price posts from Facebook sources |
| News refresh | Every 6 hours | Refresh news articles |

### Preventing duplicate scheduler runs

The scheduler starts **inside the backend process**. If you run multiple backend replicas, set `SCHEDULER_ENABLED=false` on all but one replica to prevent duplicate scraping:

```yaml
# docker-compose.prod.yml override for replica-2
environment:
  SCHEDULER_ENABLED: "false"
```

### Scheduler lock

A Python `asyncio.Lock` prevents overlapping runs within the same process. The `collection_lock` in `collector.py` ensures morning/evening/auto-discover jobs don't run concurrently.

## 8. Monitoring

### Health endpoints

| Endpoint | What it checks |
|----------|----------------|
| `GET /health` | Basic API health (`status: "ok"`) |
| `GET /api/v1/scraping/status` | Full scraper status (sources, logs, scheduler, errors) |

### Admin UI (`/admin/scraping`)

The admin panel shows:
- **Source health**: health score %, latest success/failure timestamps
- **Latest logs**: per-source records collected, duplicates, invalid, duration, admin warnings
- **Scheduler status**: running/stopped, auto-discover active, next runs
- **Aggregate stats**: total sources, active, healthy, failed, today's logs/collected
- **Facebook debug**: per-source post discovery, OCR status, block warnings

## 9. HTTPS with Let's Encrypt (optional)

Once your domain resolves to the VPS:

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --webroot -w /opt/poultry-market-intel/nginx/ssl -d yourdomain.com -d www.yourdomain.com

# Copy certs to nginx/ssl directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/
sudo chmod 644 nginx/ssl/*.pem
```

Then uncomment the HTTPS redirect block in `nginx/nginx.conf` and add an SSL server block.

Restart nginx:
```bash
docker compose -f docker-compose.prod.yml restart nginx
```

Set up auto-renewal:
```bash
sudo crontab -e
# Add:
# 0 3 * * * docker run --rm -v /opt/poultry-market-intel/nginx/ssl:/etc/letsencrypt -v /var/www/certbot:/var/www/certbot certbot/certbot renew && docker compose -f /opt/poultry-market-intel/docker-compose.prod.yml restart nginx
```

## 10. Safety checks

### Production safety validation

On startup, the backend validates:

1. **ADMIN_TOKEN must be set** when `ENV=production` — startup will fail with a clear error if missing
2. **CORS_ORIGINS** should list your production domain
3. **DEBUG** must be `false` in production

### If the backend fails to start:

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs backend

# Common errors:
# - "ADMIN_TOKEN is required when ENV=production" → set ADMIN_TOKEN in .env.production
# - PostgreSQL connection refused → wait for db healthcheck
```

## 11. Rolling updates

```bash
cd /opt/poultry-market-intel
git pull
./scripts/deploy.sh
```

## 12. Troubleshooting

### View logs

```bash
docker compose -f docker-compose.prod.yml logs -f
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
```

### Reset database

```bash
docker compose -f docker-compose.prod.yml down -v   # WARNING: destroys all data
docker compose -f docker-compose.prod.yml up -d
```

### Run migrations manually

```bash
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

## Service Architecture

```
                         ┌─────────┐
   Browser ──► 80/443 ──►│  nginx  │
                         └────┬────┘
                    ┌─────────┴──────────┐
                    ▼                    ▼
              ┌──────────┐       ┌──────────┐
              │ backend  │       │   web    │
              │ :8000    │       │ :3000    │
              └────┬─────┘       └──────────┘
                   ▼
              ┌──────────┐
              │    db    │
              │ :5432    │
              └──────────┘
```

- **nginx** terminates TLS (when configured) and routes:
  - `/api/*` → backend FastAPI
  - `/*` → Next.js web app
- **backend** runs via `python run_backend.py` and starts the scheduler automatically
- **web** calls API via relative `/api/v1/*` paths (browser → nginx → backend)
- **db** is PostgreSQL 16 with `pgdata` volume for persistence
