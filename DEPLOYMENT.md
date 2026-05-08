# Production Deployment

Phase 1 v1 launch runbook. Keep this updated when the deployment topology changes.

---

## Topology

```
              ┌──────────────────────┐
   user ───►  │  Caddy (80/443)      │  TLS via Let's Encrypt
              └──┬───────────────┬───┘
                 │               │
        psxai.example      api.psxai.example
                 │               │
              ┌──▼───┐        ┌──▼───┐
              │ web  │        │ api  │
              │:3000 │        │:8000 │
              └──────┘        └──┬───┘
                                 │
                       ┌─────────┴────────┐
                       │                  │
                  ┌────▼────┐       ┌────▼────┐
                  │ postgres │       │  redis  │
                  └─────────┘       └─────────┘
```

All five services run as containers on a single Hetzner CCX23 (4 vCPU /
16 GB / 240 GB NVMe, ~€20/mo). Vertical room for ~2k concurrent users
before we shard the DB.

---

## First-time provisioning

### 1. Server

1. Create a Hetzner Cloud project, spin up a CCX23 in **Falkenstein** or
   **Helsinki** (lowest latency to Pakistan from EU).
2. SSH in as root, harden:
   ```sh
   apt update && apt upgrade -y
   apt install -y ufw fail2ban
   ufw default deny incoming
   ufw allow OpenSSH
   ufw allow 80
   ufw allow 443
   ufw enable
   ```
3. Create a `deploy` user, copy your SSH key, disable root login.
4. Install Docker:
   ```sh
   curl -fsSL https://get.docker.com | sh
   usermod -aG docker deploy
   ```

### 2. DNS

Point an `A` record to the server IP for both:
- `psxai.example`
- `api.psxai.example`

(Caddy handles HTTPS automatically once DNS resolves.)

### 3. Application

```sh
sudo -iu deploy
git clone https://github.com/Farhan4711/psx-ai-quant-trading-intelligence.git
cd psx-ai-quant-trading-intelligence
cp .env.prod.example .env.prod
# Fill in secrets — generate with: openssl rand -hex 32
nano .env.prod
```

Edit `caddy/Caddyfile` to use your real domain.

### 4. First boot

```sh
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

Verify:
```sh
curl https://api.psxai.example/health
# {"status":"ok","version":"0.1.0"}
```

---

## Blue-green deploys

The default stack is "blue". Green runs alongside on shifted ports
(3001/8001) so traffic can swap atomically via Caddy.

```sh
# 1. Build green release
git pull
RELEASE_TAG=v0.1.1 docker compose -f docker-compose.prod.yml -p psx-green build

# 2. Run migrations against shared DB
docker compose -f docker-compose.prod.yml -p psx-green run --rm api alembic upgrade head

# 3. Bring up green stack on alt ports (override file shifts ports)
docker compose -f docker-compose.prod.yml -f docker-compose.green.yml -p psx-green up -d

# 4. Smoke-test green via direct IP/port

# 5. Swap upstreams in Caddyfile (`web:3000` → `web-green:3001`), reload:
docker compose -p psx-blue exec caddy caddy reload --config /etc/caddy/Caddyfile

# 6. Drain & drop blue:
docker compose -p psx-blue down
```

Rollback = same steps with the previous `RELEASE_TAG`.

---

## Verification checklist

After every deploy, hit each:

- [ ] `https://api.psxai.example/health` → 200 `{"status":"ok"}`
- [ ] `https://api.psxai.example/api/docs` loads
- [ ] `https://psxai.example` loads with TLS (no mixed-content warnings)
- [ ] Sentry test:
  ```sh
  curl https://api.psxai.example/health/sentry-check
  # Expect 500 in dev/staging, 404 in production. Check Sentry inbox.
  ```
- [ ] Redis cache hit ratio in Grafana > 70% after 10 min of real traffic
- [ ] Lighthouse on `/app/stocks` desktop & mobile:
  - Performance ≥ 90
  - Accessibility ≥ 95

---

## Observability

- **Sentry**: `API_SENTRY_DSN` + `WEB_SENTRY_DSN` set in `.env.prod`. Source
  maps upload at frontend build time when `SENTRY_AUTH_TOKEN` is present.
- **Grafana** + **BetterStack uptime**: not part of compose, provision
  separately or use BetterStack's free tier for uptime.

---

## Backups

Postgres dumped nightly via cron (set up after first soft-launch week):

```sh
0 3 * * * docker compose -f /home/deploy/psx-ai-quant-trading-intelligence/docker-compose.prod.yml exec -T postgres pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > /var/backups/psx-$(date +\%F).sql.gz
```

Ship dumps to Hetzner Storage Box (€3/mo, 1 TB).
