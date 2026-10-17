# ─────────────────────────────────────────────────────────────────────
# ANT (AI Note Taker) — Top-level dev workflow
#
# A `make` is a thin wrapper around the npm workspace scripts and
# Python virtualenv setup. If you don't have `make` installed:
#   - macOS: comes with Xcode Command Line Tools
#   - Linux: `apt install build-essential` (or distro equivalent)
#   - Windows: use WSL, or `choco install make`, or just call the
#     underlying commands shown in each target's `@echo` line.
# ─────────────────────────────────────────────────────────────────────

# Use bash for shell semantics (arrays, etc.) on every platform.
SHELL := /bin/bash

# Detect platform. On Windows native (no WSL), `uname` doesn't exist.
ifeq ($(OS),Windows_NT)
    PLATFORM := windows
    VENV_BIN := AINT_Venv/Scripts
    PYTHON   := python
    NPM      := npm
else
    PLATFORM := unix
    VENV_BIN := AINT_Venv/bin
    PYTHON   := python3
    NPM      := npm
endif

# The Python venv the README points contributors at.
VENV := AINT_Venv

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help (default target)
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: init setup
init: setup  ## Alias for `setup` (the conventional first-time-init name)
setup: venv install install-js  ## First-time setup: create venv, install Python + JS deps
	@echo ""
	@echo "✓ Setup complete. Activate the venv with:"
	@echo "  source $(VENV_BIN)/activate"
	@echo ""
	@echo "Then run 'make dev' to start the backend + desktop app."

.PHONY: venv
venv:  ## Create the Python virtualenv at AINT_Venv/
	test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	@echo "✓ venv ready at $(VENV)/"

.PHONY: install
install: venv  ## Install Python backend deps into the venv
	. $(VENV_BIN)/activate && pip install --upgrade pip
	. $(VENV_BIN)/activate && pip install -r backend/requirements.txt
	. $(VENV_BIN)/activate && pip install -r backend/requirements-test.txt
	@echo "✓ Python deps installed"

.PHONY: install-js
install-js:  ## Install all JS deps across workspaces (calls npm install at root)
	$(NPM) install
	@echo "✓ JS deps installed across all workspaces"

.PHONY: dev
dev:  ## Run backend + Electron desktop app together
	@echo "→ Starting backend on :8000 (Ctrl+C to stop)"
	. $(VENV_BIN)/activate && cd backend && uvicorn core.main:app --reload --port 8000 &
	@sleep 2
	@echo "→ Starting Electron app"
	cd electron && $(NPM) start

.PHONY: dev-web
dev-web:  ## Run backend + Vite web dev server (no Electron)
	@echo "→ Starting backend on :8000 (Ctrl+C to stop)"
	. $(VENV_BIN)/activate && cd backend && uvicorn core.main:app --reload --port 8000 &
	@sleep 2
	@echo "→ Starting Vite dev server on :5173"
	cd apps/web && $(NPM) run dev

.PHONY: test
test:  ## Run backend pytest suite
	. $(VENV_BIN)/activate && cd backend && pytest tests/ --ignore=tests/test_api_integration.py -q

.PHONY: test-all
test-all: test test-e2e  ## Run backend + e2e tests

.PHONY: test-e2e
test-e2e:  ## Run Playwright e2e tests (requires backend running)
	cd e2e && $(NPM) test

.PHONY: test-mobile
test-mobile:  ## Run mobile (React Native) Jest tests
	cd mobile && $(NPM) test

.PHONY: lint
lint:  ## Lint all workspaces that have a lint script
	$(NPM) run lint

.PHONY: build
build:  ## Build production web + electron bundles
	$(NPM) run build

.PHONY: build-web
build-web:  ## Build only the web SPA
	$(NPM) run web:build

.PHONY: build-electron
build-electron:  ## Build only the Electron distributable for current platform
	$(NPM) run electron:build

.PHONY: mobile-install mobile-android mobile-ios
mobile-install:  ## Install mobile (React Native) deps
	cd mobile && $(NPM) install
	@echo "✓ mobile deps installed"

mobile-android:  ## Build + run mobile on Android emulator
	cd mobile && $(NPM) run android

mobile-ios:  ## Build + run mobile on iOS simulator
	cd mobile && $(NPM) run ios

.PHONY: audit
audit:  ## Print the project audit doc path
	@echo "→ Project audit: docs/AUDIT_2026-06-05_Project_Audit.md"

.PHONY: helm-vendor
helm-vendor:  ## Vendor bitnami/common dependency for the helm chart
	cd k8s/helm/backend && helm dependency build
	@echo "✓ helm chart dependencies vendored"

.PHONY: docker-up
docker-up:  ## Start the local docker-compose stack (backend + neo4j)
	docker compose -f docker/docker-compose.yml up

.PHONY: docker-up-full
docker-up-full:  ## Start the full stack with neo4j, postgres, redis, monitoring
	docker compose -f docker/docker-compose.yml --profile with-neo4j --profile with-postgres --profile with-redis --profile with-monitoring up

.PHONY: docker-down
docker-down:  ## Stop the local docker-compose stack
	docker compose -f docker/docker-compose.yml down

.PHONY: pwa-icons
pwa-icons:  ## Regenerate apps/web PWA icons from assets/design/source/Ant_App_icon.png
	$(PYTHON) scripts/generate_pwa_icons.py

.PHONY: alembic-upgrade
alembic-upgrade:  ## Run alembic upgrade head (apply DB migrations)
	. $(VENV_BIN)/activate && cd backend && alembic upgrade head

.PHONY: alembic-downgrade
alembic-downgrade:  ## Run alembic downgrade base (revert all DB migrations)
	. $(VENV_BIN)/activate && cd backend && alembic downgrade base

.PHONY: alembic-revision
alembic-revision:  ## Generate a new alembic revision (autogenerate). MSG="your message"
	@if [ -z "$(MSG)" ]; then echo "Usage: make alembic-revision MSG=\"add foo table\""; exit 1; fi
	. $(VENV_BIN)/activate && cd backend && alembic revision --autogenerate -m "$(MSG)"

.PHONY: clean
clean:  ## Remove build artifacts (NOT the venv, NOT node_modules)
	rm -rf apps/web/dist electron/dist backend/.pytest_cache backend/htmlcov backend/coverage.xml
	rm -rf apps/web/.vite electron/.vite
	@find . -type d -name "__pycache__" -not -path '*/venv/*' -not -path '*/AINT_Venv/*' -exec rm -rf {} + 2>/dev/null || true
	@echo "✓ build artifacts removed (run 'make clean-all' for nuke)"

.PHONY: clean-all
clean-all:  ## Remove ALL build artifacts INCLUDING venv + node_modules
	rm -rf $(VENV) backend/venv node_modules apps/*/node_modules electron/node_modules mobile/node_modules e2e/node_modules
	@echo "✓ nuked. Run 'make setup' to rebuild from scratch."

.PHONY: verify
verify:  ## Run all checks: lint, test, e2e (CI-equivalent local gate)
	$(NPM) run lint
	@make test
	@echo ""
	@echo "✓ All checks passed."
