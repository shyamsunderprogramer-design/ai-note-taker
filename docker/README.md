# Docker — Multi-target container images

The `docker/` directory holds the **alternative / self-host** Dockerfiles.
The `Dockerfile` at the repo root is the one Render uses for the
production cloud deploy (`render.yaml`).

## Which Dockerfile do I use?

| Target                | Dockerfile                  | Use it for                                                       |
|-----------------------|-----------------------------|------------------------------------------------------------------|
| **Render (cloud)**    | `./Dockerfile`              | Default cloud deploy. Reads `render.yaml` env vars.              |
| **Self-host backend** | `docker/Dockerfile.backend` | `docker compose up backend` for local dev. Includes Neo4j sidecar. |
| **Self-host cloud**   | `docker/Dockerfile.cloud`   | Multi-region cloud image (smaller, no ML deps). For Docker Swarm / k8s. |
| **Electron build**    | `docker/Dockerfile.electron`| CI builds for Windows / macOS / Linux Electron distributables.   |

## What's in here

```
docker/
├── Dockerfile.backend      # FastAPI backend (production target)
├── Dockerfile.cloud        # FastAPI backend (cloud-minimal target)
├── Dockerfile.electron     # Electron builder (CI only)
├── docker-compose.yml       # backend + neo4j for local dev
├── prometheus.yml           # scrape config for the /metrics endpoint
└── alert_rules.yml          # Prometheus alerting rules
```

## Local development with docker-compose

The fastest path to a working backend + Neo4j stack:

```bash
cp .env.example .env
# Fill in at least one of OPENAI_API_KEY / ANTHROPIC_API_KEY / etc.
# Neo4j is OPTIONAL — leave NEO4J_PASSWORD blank to skip the sidecar.

docker compose -f docker/docker-compose.yml up
# Backend on :8000, Neo4j browser on :7474, Neo4j bolt on :7687
```

The compose file mounts `./backend` and `./data` into the container
so live-reload works — edits to `core/main.py` or any route module
are picked up by uvicorn's `--reload` without rebuilding the image.

## Production self-host

For a production-grade self-host (NOT Render), use `docker/Dockerfile.cloud`:

```bash
docker build -f docker/Dockerfile.cloud -t ant-backend:prod .
docker run -d \
  --name ant-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/ant \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e ENCRYPTION_KEY="$(openssl rand -hex 32)" \
  -e CORS_ORIGINS=https://your.domain \
  -e AUTH_REQUIRED=true \
  -e FORCE_SQLITE=false \
  -e EMBEDDING_ENABLED=true \
  -e CLASSIFIER_ENABLED=true \
  ant-backend:prod
```

## Prometheus / Grafana

`prometheus.yml` is a minimal scrape config that points at the
backend's `/metrics` endpoint (added by Fix #43, see audit doc).
The backend exposes Prometheus-format metrics when the optional
`prometheus-client` package is installed (it is in `requirements.txt`).

`alert_rules.yml` has 3 starter alerts:
- `BackendDown` — 5xx error rate > 50% over 5 min
- `SlowResponses` — p99 latency > 5s over 10 min
- `HighMemory` — RSS > 800MB sustained for 15 min

Tune the thresholds in `alert_rules.yml` to match your SLOs.

## CI

`docker/Dockerfile.electron` is used by `.github/workflows/ci.yml`'s
electron-build job (when added — see audit Fix #43 followup). It pulls
the heavy electron-builder image to produce platform-specific
distributables in CI without polluting the dev environment.
