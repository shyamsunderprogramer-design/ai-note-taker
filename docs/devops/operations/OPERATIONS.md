# Operations Runbook

> Production runbook for the ANT (AI Note Taker) backend. For day-to-day dev commands, see [DEVELOPMENT.md](DEVELOPMENT.md). For common errors, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## 1. Health checks

### Liveness

```bash
curl -fsS https://ai-note-taker-7xvn.onrender.com/health
# → {"status": "ok", "version": "1.0.0", "uptime_seconds": 3600}
```

### Readiness (DB + cognitive graph)

```bash
curl -fsS https://ai-note-taker-7xvn.onrender.com/health/database
# → {"status": "ok", "engine": "postgresql", "tables": 13, "alembic_version": "f78f0efa440e"}

curl -fsS https://ai-note-taker-7xvn.onrender.com/health/modules
# → {"status": "ok", "modules": {"ai_router": true, "whisper": true, "neo4j": true, ...}}
```

### Detailed config dump (debug only)

```bash
curl -fsS -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://ai-note-taker-7xvn.onrender.com/health/config
# → returns effective runtime config (no secrets, but lists which
#   env vars are set + which features are enabled)
```

---

## 2. Backup & restore

### SQLite (dev / single-tenant)

```bash
# Backup
sqlite3 backend/data/ainotetaker.db ".backup /var/backups/ant/$(date +%F).db"

# Restore
cp /var/backups/ant/2026-06-08.db backend/data/ainotetaker.db
# then restart the backend so the SQLite connection reopens the file
```

### PostgreSQL (production)

```bash
# Backup
pg_dump "$DATABASE_URL" --format=custom \
  --file=/var/backups/ant/$(date +%F).dump

# Restore
pg_restore --dbname="$DATABASE_URL" --clean --if-exists \
  /var/backups/ant/2026-06-08.dump
```

### Triggered backup via API (admin only)

```bash
curl -fsS -X POST -H "Authorization: Bearer $ADMIN_TOKEN" \
  https://ai-note-taker-7xvn.onrender.com/admin/backup
# → creates a snapshot in /var/backups/ant/ and returns the path
```

---

## 3. Logs

### Backend (Python)

Logs are JSON lines, written to stdout (Render captures these) and to `backend/data/audit_logs/audit.jsonl` for user-action events only.

```bash
# Tail audit log
tail -f backend/data/audit_logs/audit.jsonl | jq

# Filter by event type
jq 'select(.event == "auth.login")' backend/data/audit_logs/audit.jsonl

# Filter by user
jq 'select(.user_id == "default")' backend/data/audit_logs/audit.jsonl
```

### Electron desktop (per-machine)

The Electron app uses `electron-log` to write to platform-specific locations:

- **macOS:** `~/Library/Logs/ANT/main.log`
- **Windows:** `%APPDATA%\ANT\logs\main.log`
- **Linux:** `~/.config/ANT/logs/main.log`

```bash
# Tail on macOS
tail -f ~/Library/Logs/ANT/main.log
```

---

## 4. Database migrations (Alembic)

> See [MIGRATIONS.md](MIGRATIONS.md) for the full developer guide. This section is the ops runbook.

### Apply pending migrations

```bash
# Local
make alembic-upgrade

# Production (Render)
# Migrations are run automatically by DatabaseManager.initialize() at
# startup, BEFORE the legacy create_all() call. To run them
# out-of-band (e.g., to fail fast on a bad migration), exec into the
# Render shell and run:
alembic upgrade head
```

### Check current version

```bash
alembic current
# → f78f0efa440e (head)
alembic history
# → shows all revisions, newest first
```

### Roll back

```bash
# Roll back the most recent migration
alembic downgrade -1

# Roll back to base (drop everything)
alembic downgrade base
# WARNING: this drops all 13 tables. Only do this in dev/staging.
```

### Recover from a failed migration

If `alembic upgrade head` errors partway through, the `alembic_version` row may be left in a state that doesn't match the actual schema. To recover:

```bash
# 1. Check what's in the DB
alembic current

# 2. If the version is wrong, stamp it manually
alembic stamp head

# 3. Or stamp a specific revision if you need to "skip" a bad one
alembic stamp <revision_id>
```

---

## 5. Roll back a deploy

### Render

1. Render dashboard → service → **Manual Deploy** → pick the previous commit from the deploy history.
2. Wait for the build to complete (the new instance will spin up before the old one is killed).
3. Verify with `curl /health` that the new instance is up.

### Kubernetes (when self-hosting)

```bash
# Check rollout history
kubectl rollout history deployment/ant-backend -n ant

# Roll back to previous revision
kubectl rollout undo deployment/ant-backend -n ant

# Roll back to a specific revision
kubectl rollout undo deployment/ant-backend -n ant --to-revision=3
```

---

## 6. Cognitive graph (Neo4j)

### Health

```bash
# Bolt protocol
curl -fsS http://neo4j:7474/
# → 200 OK (HTTP root)

# CQL queries via the cypher-shell
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n) RETURN count(n)"
```

### Backup

Neo4j uses its own backup tool, not pg_dump. See [Neo4j backup docs](https://neo4j.com/docs/operations-manual/current/backup-restore/).

```bash
# Stop the database (or use a hot backup tool like Neo4j Enterprise)
neo4j-admin backup --backup-dir=/var/backups/neo4j/ \
  --name=ant-$(date +%F).backup

# Restore
neo4j-admin restore --from=/var/backups/neo4j/ant-2026-06-08.backup \
  --database=neo4j --force
```

### Reset (dev only)

```bash
# Wipe all data
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "MATCH (n) DETACH DELETE n"

# Drop all indexes
cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "DROP INDEX ON :Skill(name)"
# (use the schema dump to recreate)
```

---

## 7. On-call checklist

When the alarm fires:

1. **Check the dashboard** — is it a single-route 500, a region-wide outage, or a deploy-related regression?
2. **Hit `/health`** — is the process up? If not, check Render logs.
3. **Check recent deploys** — Render → Deploys. If one shipped in the last 30 min, roll it back.
4. **Check the database** — `/health/database` and `/health/modules`. If alembic is broken, see section 4.
5. **Check Neo4j** — is the cognitive-graph profile enabled? Are credentials correct?
6. **Check third-party providers** — `curl https://status.openai.com/`, `https://status.anthropic.com/`, etc. AI failures are often provider-side, not ours.
7. **Communicate** — post in the team's Slack channel with what you found.

### Common alarms

| Alarm | First thing to check |
|---|---|
| 5xx spike | `/health/modules` — which module failed to import? |
| Slow responses | Neo4j (`bolt://neo4j:7687`) latency — is the bolt port reachable? |
| Auth failures spike | JWT secret rotation? `JWT_SECRET_KEY` env var still set? |
| Upload failures | `/var/lib/ant/` write permission? Disk space? |
| WebSocket disconnects | Reverse proxy timeout? Render's proxy times out at 5 min idle. |

---

## 8. Cost monitoring

- **Render free tier** — 750 hours/month of web service, 100 GB egress. Check Render → Usage.
- **Ollama cloud** — token-based pricing; usage is in the Ollama dashboard.
- **Cloud AI providers** — each has its own usage dashboard; the backend logs token counts per request to `audit.jsonl`.
- **Neo4j** — Aura free tier (50k nodes, 50k relationships); self-hosted = whatever the VM costs.

---

## 9. Disaster recovery

### Database

- **PostgreSQL** — daily `pg_dump` to S3 (or equivalent). Retain 7 daily + 4 weekly + 12 monthly.
- **SQLite** — daily `cp` to S3. Retain 7 daily.
- **Neo4j** — daily `neo4j-admin backup` to S3. Retain 7 daily.

### Code

- All code is in git. The `main` branch is the source of truth. Releases are tagged.

### Config

- `.env.example` is in git. Production env vars live in Render. Render's `generateValue: true` keys (like `JWT_SECRET_KEY`) are in the service's "Environment" tab and can be exported.

### Recovery time objectives (RTOs)

- Single-instance failure: < 2 min (Render restarts automatically)
- Database corruption: < 30 min (restore from latest backup)
- Region failure: 1-2 hours (manual deploy to a different region)
