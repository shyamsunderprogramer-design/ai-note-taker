# Docker Runtime Notes

> **Role tag:** `devops`
> **Owner:** `role-devops`

---

## What goes here

Notes about the Docker setup that don't fit in the Dockerfile
itself or in the deployment guide. The current Docker setup is:

- Root `Dockerfile` — multi-stage build (frontend + backend)
- `docker/` — supplementary scripts, init scripts for Neo4j,
  docker-compose overrides
- `.dockerignore` — exclusion list

The Dockerfile and `.dockerignore` are co-owned by devops +
devsecops (attack-surface changes require both).

---

## Local dev

```bash
# Build the image
docker build -t ant-dev .

# Run the container
docker run --rm -p 8000:8000 \
  -v $(pwd)/backend/data:/app/backend/data \
  ant-dev

# Or use docker-compose for a full stack (api + neo4j)
docker compose -f docker/docker-compose.yml up
```

---

## Neo4j init scripts

Neo4j container is initialized from
`docker/neo4j-init/` mounted to `/docker-entrypoint-initdb.d/`.
That includes the index definitions and a default admin user
override (see `Phase 7 K8s + Docker polish` memory).

---

## Image security

- Base image pinned in `Dockerfile` (no `latest` tag).
- `trivy-scan.sh` runs in CI; see
  [`docs/devsecops/supply-chain/`](../devsecops/supply-chain/).
- Multi-stage build keeps build-time deps out of the runtime
  image.

---

## Known gotchas

- The `backend/data/` volume must be writable by the in-container
  user (UID 1000 in the current Dockerfile).
- The Neo4j container needs `APOC` plugin enabled for some
  cognitive-graph queries — the init scripts handle this.

---

*Last Updated: 2026-06-11 — created as part of the role-ownership refactor*
