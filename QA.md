# Pre-Launch QA Checklist

## 1. Production Smoke Test (Docker Compose)

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 1.1 | `docker compose -f docker-compose.prod.yml up -d` | All containers start without errors | ⬜ |
| 1.2 | `GET /health` | `{"status":"ok"}` | ⬜ |
| 1.3 | `GET /api/v1/prices/latest` | Returns price array (may be empty) | ⬜ |
| 1.4 | `/api/v1/scraping/status` (no token) | Returns status publicly (GET only) | ⬜ |
| 1.5 | `POST /api/v1/scraping/run` (no token) | `401` with Arabic error | ⬜ |
| 1.6 | `POST /api/v1/scraping/run` (correct `X-Admin-Token`) | Runs collection, returns status (local dev = `8191`) | ⬜ |
| 1.7 | Scheduler status visible in Admin UI | Shows running/stopped, auto-discover info | ⬜ |
| 1.8 | `ENV=production` + empty `ADMIN_TOKEN` | Backend fails to start with clear error | ⬜ |

## 2. Backup Verification

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 2.1 | Run `scripts/backup_postgres.bat` | Creates `.sql` file in `backups/` | ⬜ |
| 2.2 | Restore command works | `type backup.sql \| docker exec -i db psql -U poultry -d poultry_market` | ⬜ |
| 2.3 | Old backups cleaned (14 days) | `forfiles /p backups /m *.sql /d -14 /c "cmd /c del @path"` | ⬜ |

## 3. UI Checks

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 3.1 | Homepage BrandCredit splash | Hero variant shows on load, fades after 1.8s | ⬜ |
| 3.2 | Non-homepage BrandCredit | Footer variant in sidebar bottom-right | ⬜ |
| 3.3 | Dashboard latest prices | Shows real prices from API with `raw_product_name`, source, date | ⬜ |
| 3.4 | Dashboard empty state | Shows "لا توجد بيانات سوق كافية بعد" when no data | ⬜ |
| 3.5 | Prices page product filter | Filters by fertilized_eggs / day_old_chicks / feed | ⬜ |
| 3.6 | Prices page category filter | Filters by white/sasso/baladi/local/duck/quail/turkey/ostrich/brown | ⬜ |
| 3.7 | Prices page source filter | Filters by unique source names | ⬜ |
| 3.8 | Admin source cards | Shows `latest_log` per source (valid_saved, duplicates_skipped, invalid_skipped) | ⬜ |
| 3.9 | Admin scheduler details | Shows running status, auto-discover interval, last run time | ⬜ |

## 4. Scraping

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 4.1 | Source 25 auto-discover | Runs without crashing, discovers posts if any | ⬜ |
| 4.2 | Source 26 Facebook block | Shows `admin_warning` about image-only content; does not crash system | ⬜ |
| 4.3 | Duplicate run on same data | Existing records skipped (`duplicates_skipped` increments, no copies created) | ⬜ |
| 4.4 | Manual price entry | Saves via `POST /api/v1/prices/manual` with token | ⬜ |

## 5. Security

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 5.1 | Protected POST/PATCH/DELETE without token | `401` + Arabic "هذه العملية تتطلب صلاحية مدير" | ⬜ |
| 5.2 | Protected GET (debug/facebook-debug/ocr-preview) without token | `401` | ⬜ |
| 5.3 | Public GET endpoints without token | `200` (`/health`, `/prices/latest`, `/scraping/status`, `/scraping/sources`, `/scraping/logs`, `/news/*`, `/predictions/*`, `/holidays/*`) | ⬜ |
| 5.4 | `Authorization: Bearer <token>` works | Protected endpoints succeed | ⬜ |
| 5.5 | `X-Admin-Token: <token>` works | Protected endpoints succeed | ⬜ |
| 5.6 | Frontend 401 handling | Token cleared from localStorage, error toast "هذه العملية تتطلب صلاحية مدير" | ⬜ |
| 5.7 | Token prompt in Admin UI | Shown when no token stored; saved to localStorage on submit | ⬜ |

## 6. Tests

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 6.1 | Backend pytest | 62/62 passed, no failures | ✅ |
| 6.2 | TypeScript check | `npx tsc --noEmit` — zero errors | ✅ |
| 6.3 | Frontend build | `npm run build` — succeeds | ⬜ |
| 6.4 | Docker Compose build | `docker compose -f docker-compose.prod.yml build` — all images build | ⬜ |

## 7. Deployment

| # | Check | Expected | Status |
|---|-------|----------|--------|
| 7.1 | `.env.production` created from `.env.production.example` | All vars filled (local dev uses `8191`; prod must use a strong random token) | ⬜ |
| 7.2 | Alembic migrations run | `alembic upgrade head` succeeds | ⬜ |
| 7.3 | HTTPS cert configured (optional) | certbot + nginx SSL block active | ⬜ |
| 7.4 | `SCHEDULER_ENABLED=false` on replica 2+ | No duplicate scheduler runs | ⬜ |
| 7.5 | Daily backup cron installed | `0 2 * * * ./scripts/backup-db.sh` | ⬜ |

---

**Legend**: ✅ Passed · ⬜ Pending · ❌ Failed
