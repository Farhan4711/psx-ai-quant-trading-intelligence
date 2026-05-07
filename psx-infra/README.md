# psx-infra — Infrastructure & Deployment

Docker Compose stacks, CI/CD configs, and deployment scripts.

## Local Full-Stack Development

```bash
cd psx-infra
cp .env.example .env
docker compose -f docker-compose.dev.yml up -d
```

This starts: PostgreSQL 15 + TimescaleDB, Redis 7, (optionally) pgAdmin.

Databases created automatically: `psx_dev`, `psx_test`, `psx_staging`

## Files (to be created in Step 6)

| File | Purpose |
|---|---|
| `docker-compose.dev.yml` | Local dev: Postgres + TimescaleDB + Redis |
| `docker-compose.staging.yml` | Full staging stack on Hetzner |
| `docker-compose.prod.yml` | Production stack |
| `Caddyfile` | Reverse proxy config (HTTPS, routing) |
| `prometheus/` | Prometheus scrape config |
| `grafana/` | Dashboard JSON exports |
| `scripts/backup.sh` | pg_dump to R2/S3 |
| `scripts/restore.sh` | Restore from backup (tested quarterly) |

## Server Hardening Checklist (Step 5)

- [ ] SSH key-only authentication (`PasswordAuthentication no`)
- [ ] fail2ban installed and configured (SSH + nginx/caddy)
- [ ] ufw firewall: allow only 22 (SSH), 80 (HTTP), 443 (HTTPS)
- [ ] Separate application user (no sudo) for running Docker containers
- [ ] Automatic security updates enabled (`unattended-upgrades`)
- [ ] Docker daemon socket not exposed externally
