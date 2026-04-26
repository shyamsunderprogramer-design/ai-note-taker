# AI Note Taker — Zero-Cost Deployment Guide

> **Complete step-by-step guide to deploy AI Note Taker to the cloud for FREE**
> Last updated: 2026-04-26

---

## Architecture Overview

```
┌─────────────────────┐      ┌──────────────────────┐      ┌────────────────┐
│   Vercel (Free)      │─────▶│  Render Free Tier    │─────▶│  Neon Free     │
│   Frontend Host      │ CORS │  FastAPI Backend      │      │  PostgreSQL    │
│   ant-note-taker.     │      │  ant-backend.         │      │  Serverless    │
│   vercel.app          │      │  onrender.com         │      │                │
└─────────────────────┘      └──────────────────────┘      └────────────────┘
         │                            │
         │    HTTPS + CORS            │
         └────────────────────────────┘
```

| Component | Free Tier | Limits |
|-----------|-----------|--------|
| **Vercel** | Hobby plan | 100GB bandwidth/month, auto-deploys from GitHub |
| **Render** | Free web service | 512MB RAM, 750hrs/month, sleeps after 15min idle |
| **Neon** | Free tier | 0.5GB storage, 100 compute hours/month, auto-suspend 5min |
| **GitHub Actions** | Free for public repos | 2000 min/month |

### What works on cloud vs local-only

| Feature | Cloud (Render) | Local (Electron) |
|---------|-----------------|-------------------|
| Text chat (AI providers) | Yes (needs API key) | Yes (Ollama or API key) |
| Note-taking | Yes | Yes |
| Authentication | Yes | Yes |
| Voice transcription | No (Whisper needs GPU) | Yes |
| Embeddings/semantic search | No (512MB RAM) | Yes |
| Cognitive graph (Neo4j) | No | Yes |
| Ollama local models | No | Yes |
| Voice cloning | No (Windows-only) | Yes |

---

## Phase 0: Create Accounts (No Credit Card Required)

### Step 0.1: GitHub

1. Go to https://github.com/signup
2. Create a free account
3. Verify your email
4. Create a **public** repository named `ai-note-taker`
5. Push your code:
   ```bash
   git remote add origin https://github.com/<YOUR_USERNAME>/ai-note-taker.git
   git push -u origin main
   ```
   > **Important**: The repo must be **public** for free GitHub Actions.

### Step 0.2: Render

1. Go to https://dashboard.render.com/register
2. Sign up using your **GitHub account** (SSO) — this links the two
3. No credit card required for the free tier

### Step 0.3: Vercel

1. Go to https://vercel.com/signup
2. Sign up using your **GitHub account** (SSO)
3. No credit card required for the Hobby plan

### Step 0.4: Neon (PostgreSQL)

1. Go to https://neon.tech/app/signup
2. Sign up using your **GitHub account** (SSO)
3. No credit card required for the free tier

---

## Phase 1: Local Development Setup

### Step 1.1: Python Virtual Environment

```bash
cd D:/Rep/ai-note-taker/backend

# Create virtual environment
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-security.txt
```

### Step 1.2: Configure Environment

```bash
# Copy the example config
cp .env.example .env
```

Edit `backend/.env` with local development values:
```env
FORCE_SQLITE=true
AUTH_REQUIRED=false
CORS_ALLOW_ALL=true
EMBEDDING_ENABLED=true
CLASSIFIER_ENABLED=true
OLLAMA_URL=http://localhost:11434
ENCRYPTION_KEY=dev-only-32-char-key-00000000
```

### Step 1.3: Start the Backend

```bash
cd D:/Rep/ai-note-taker/backend
uvicorn core.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 1.4: Verify Local Setup

Open your browser:
- **Health check**: http://127.0.0.1:8000/health → should return `{"status":"ok"}`
- **Module status**: http://127.0.0.1:8000/health/modules
- **Frontend**: Open `apps/web/index.html` in a browser

Or use Electron:
```bash
cd D:/Rep/ai-note-taker/electron
npm install
npm start
```

---

## Phase 2: Cloud Deployment

### Step 2.1: Set Up Neon PostgreSQL Database

1. Log into https://console.neon.tech
2. Click **"New Project"**
3. Name it: `ant-note-taker`
4. Select region: **US East (N. Virginia)** — closest to Render free tier
5. Click **"Create Project"**
6. Neon provides a connection string:
   ```
   postgresql://neondb_owner:AbCdEf123456@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
7. **Convert it to asyncpg format** (change `postgresql://` to `postgresql+asyncpg://`):
   ```
   postgresql+asyncpg://neondb_owner:AbCdEf123456@ep-cool-name-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
8. **Save this string** — you'll need it for Render

```
┌─────────────────────────────────────────────────────────┐
│  Neon Dashboard                                         │
│                                                          │
│  Project: ant-note-taker                                 │
│  Region: US East                                         │
│  Status: Active                                          │
│                                                          │
│  Connection String:                                      │
│  postgresql+asyncpg://neondb_owner:****@ep-...neon.tech  │
│                                                          │
│  ⚠️ Copy this now — you'll need it for Render!          │
└─────────────────────────────────────────────────────────┘
```

### Step 2.2: Deploy Backend on Render

1. Log into https://dashboard.render.com
2. Click **"New"** → **"Web Service"**
3. Click **"Build an existing repository from GitHub"**
4. Select your `ai-note-taker` repository
5. Configure:
   - **Name**: `ant-backend`
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r backend/requirements-cloud.txt`
   - **Start Command**: `cd backend && uvicorn core.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Instance Type**: **Free**
6. Click **"Advanced"** → Add environment variables:

   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `postgresql+asyncpg://neondb_owner:****@ep-...neon.tech/neondb?sslmode=require` |
   | `FORCE_SQLITE` | `false` |
   | `EMBEDDING_ENABLED` | `false` |
   | `CLASSIFIER_ENABLED` | `false` |
   | `AUTH_REQUIRED` | `true` |
   | `CORS_ALLOW_ALL` | `false` |
   | `HTTPS_REQUIRED` | `true` |
   | `ENCRYPTION_KEY` | Generate with: `openssl rand -hex 16` |
   | `OPENAI_API_KEY` | *(optional — at least one AI key recommended)* |

7. Click **"Create Web Service"**
8. Wait for the initial build (3-5 minutes)
9. Note your URL: `https://ant-backend.onrender.com`

```
┌─────────────────────────────────────────────────────────┐
│  Render Dashboard                                        │
│                                                          │
│  Service: ant-backend                                    │
│  URL: https://ant-backend.onrender.com                   │
│  Status: 🟢 Live                                        │
│  Region: Oregon, USA                                     │
│  Plan: Free                                              │
│                                                          │
│  Environment Variables:                                   │
│  DATABASE_URL    = postgresql+asyncpg://...              │
│  FORCE_SQLITE    = false                                  │
│  EMBEDDING_ENABLED = false                                │
│  CLASSIFIER_ENABLED = false                               │
│  AUTH_REQUIRED   = true                                   │
│  CORS_ALLOW_ALL  = false                                  │
│  HTTPS_REQUIRED  = true                                   │
│  ENCRYPTION_KEY  = <generated>                            │
└─────────────────────────────────────────────────────────┘
```

### Step 2.3: Deploy Frontend on Vercel

1. Log into https://vercel.com/dashboard
2. Click **"Add New"** → **"Project"**
3. Import your `ai-note-taker` GitHub repository
4. Configure:
   - **Framework Preset**: **Other**
   - **Root Directory**: Leave as default (`.`)
   - **Build Command**: Leave empty (static site, no build)
   - **Output Directory**: `apps/web`
5. Click **"Deploy"**
6. Wait 1-2 minutes
7. Note your URL: `https://ant-note-taker.vercel.app`

```
┌─────────────────────────────────────────────────────────┐
│  Vercel Dashboard                                        │
│                                                          │
│  Project: ai-note-taker                                  │
│  URL: https://ant-note-taker.vercel.app                  │
│  Status: 🟢 Ready                                        │
│  Framework: Other (Static)                               │
│  Output: apps/web                                         │
│                                                          │
│  Auto-deploys: On push to main                           │
└─────────────────────────────────────────────────────────┘
```

### Step 2.4: Connect Frontend to Backend (CORS)

After both services are deployed:

1. Go to **Render Dashboard** → `ant-backend` → **Environment**
2. Add/update: `CORS_VERCEL_URL` = `ant-note-taker.vercel.app`
3. Render will auto-redeploy with the new CORS setting
4. Update `apps/web/js/core/config.js` if your Render URL is different from `ant-backend.onrender.com`

The CORS flow:
```
Browser (Vercel)                 Backend (Render)
        │                              │
        │  GET /health                 │
        │  Origin: ant-note-taker.     │
        │          vercel.app           │
        │─────────────────────────────▶│
        │                              │
        │  CORS check:                 │
        │  Is "ant-note-taker.         │
        │  vercel.app" in              │
        │  ALLOWED_ORIGINS?            │
        │  ✅ Yes (via CORS_VERCEL_URL) │
        │                              │
        │  200 OK + CORS headers       │
        │◀─────────────────────────────│
```

---

## Phase 3: Verification

### Step 3.1: Backend Health Check

```bash
curl https://ant-backend.onrender.com/health
```

Expected response:
```json
{"status":"ok","service":"ai-backend"}
```

### Step 3.2: Database Connectivity

```bash
curl https://ant-backend.onrender.com/health/database
```

Expected response:
```json
{"available":true,"connected":true}
```

### Step 3.3: Frontend Test

1. Open https://ant-note-taker.vercel.app in your browser
2. Open DevTools Console (F12)
3. Verify: `window.API_BASE` should be `"https://ant-backend.onrender.com"`
4. The sign-in page should load
5. Try registering a new account

### Step 3.4: CORS Test

```bash
curl -H "Origin: https://ant-note-taker.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://ant-backend.onrender.com/health
```

Should return CORS headers including:
```
access-control-allow-origin: https://ant-note-taker.vercel.app
```

### Step 3.5: Cold Start Test

Render free tier sleeps after 15 minutes of inactivity:

1. Wait 15+ minutes (or manually restart the service)
2. Visit your Vercel URL
3. First request will take ~30 seconds (cold start)
4. Subsequent requests should be fast (<500ms)

> **Tip**: To reduce cold starts, set up UptimeRobot (free) to ping `/health` every 5 minutes.
> Note: Render free tier still sleeps regardless, but this keeps it warm during active hours.

---

## Phase 4: Monitoring (Free)

### UptimeRobot (Free — 50 monitors)

1. Go to https://uptimerobot.com and create a free account
2. Add monitors:
   - `https://ant-backend.onrender.com/health` (HTTP monitor, 5-min interval)
   - `https://ant-note-taker.vercel.app` (HTTP monitor, 5-min interval)
3. Enable email alerts for downtime

### Render Built-in Monitoring

- Render dashboard → your service → **Logs** tab for real-time logs
- Render dashboard → your service → **Metrics** for request count, response time, error rate

### Vercel Analytics

- Vercel dashboard → your project → **Analytics** tab
- Core Web Vitals tracking (free)

### GitHub Actions Health Check

Already configured in `.github/workflows/health-check.yml`:
- Runs every 30 minutes
- Checks both backend and frontend endpoints
- Fails the workflow if either is down

---

## Phase 5: Updating the Deployment

### Automatic Deploys

Both Vercel and Render auto-deploy when you push to the `main` branch:

```bash
git add .
git commit -m "Update feature X"
git push origin main
```

- **Vercel**: Deploys in ~1 minute
- **Render**: Builds and deploys in ~3-5 minutes

### Manual Redeploy

- **Render**: Dashboard → your service → **Manual Deploy** → **Deploy latest commit**
- **Vercel**: Dashboard → your project → **Deployments** → **Redeploy**

### Environment Variable Changes

On Render, changing environment variables triggers an automatic redeploy.

---

## Troubleshooting

### Common Issues

| Problem | Solution |
|---------|----------|
| **502 Bad Gateway on Render** | Check Render logs — backend may have crashed. Common cause: missing env var or import error |
| **CORS error in browser** | Verify `CORS_VERCEL_URL` matches your Vercel URL exactly (no `https://` prefix) |
| **Cold start too slow** | Render free tier sleeps after 15min idle — this is expected. Upgrade to paid ($7/mo) for always-on |
| **Database connection error** | Verify `DATABASE_URL` uses `postgresql+asyncpg://` prefix and `?sslmode=require` |
| **Frontend shows blank page** | Check browser console for `API_BASE` value and CORS errors |
| **ML features not working** | Expected — Whisper, embeddings, spacy are disabled on cloud (512MB RAM limit). Use local dev for ML features |
| **Authentication errors** | Verify `ENCRYPTION_KEY` is set (32+ characters). Regenerate with `openssl rand -hex 16` |

### Checking Logs

- **Render**: Dashboard → your service → **Logs** tab
- **Vercel**: Dashboard → your project → **Deployments** → click deployment → **Function Logs**
- **Neon**: Console → your project → **Metrics** tab

### Database Management

```bash
# Check Neon database from your local machine
psql postgresql://neondb_owner:PASSWORD@ep-HOST.neon.tech/neondb

# Or use Neon's SQL Editor in the web console
```

---

## Quick Reference: Environment Variables

### Render (Backend)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | Neon PostgreSQL connection string |
| `FORCE_SQLITE` | No | `false` | Set to `true` to use SQLite instead |
| `AUTH_REQUIRED` | No | `true` | Enable authentication |
| `ENCRYPTION_KEY` | Yes | — | 32-char key for data encryption |
| `CORS_ALLOW_ALL` | No | `false` | Allow all origins (dev only) |
| `CORS_VERCEL_URL` | Yes | — | Vercel frontend domain (e.g., `ant-note-taker.vercel.app`) |
| `HTTPS_REQUIRED` | No | `true` | Enforce HTTPS |
| `EMBEDDING_ENABLED` | No | `false` | Enable ML embeddings (not recommended on free tier) |
| `CLASSIFIER_ENABLED` | No | `false` | Enable ML classifier (not recommended on free tier) |
| `OPENAI_API_KEY` | No | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | — | Anthropic API key |
| `GOOGLE_API_KEY` | No | — | Google API key |
| `GROQ_API_KEY` | No | — | Groq API key |

### Vercel (Frontend)

No environment variables needed — `config.js` auto-detects the backend URL.

---

## Architecture Diagram

```
                    ┌──────────────────────────────┐
                    │        User's Browser         │
                    └──────────────┬───────────────┘
                                   │
                          ┌────────▼────────┐
                          │   Vercel CDN      │
                          │   (Static Files)  │
                          │                   │
                          │  index.html       │
                          │  app.js           │
                          │  style.css        │
                          │  config.js ───────┼──▶ Sets API_BASE
                          │  sw.js            │     to Render URL
                          └────────┬──────────┘
                                   │
                          ┌────────▼────────┐
                          │  Render Backend   │
                          │  (FastAPI)        │
                          │                   │
                          │  /health           │
                          │  /auth/*           │
                          │  /ai/*             │
                          │  /conversations/*  │
                          │  /analytics/*      │
                          │  ...               │
                          └────────┬──────────┘
                                   │
                          ┌────────▼────────┐
                          │  Neon PostgreSQL  │
                          │  (Serverless)     │
                          │                   │
                          │  Users            │
                          │  Conversations    │
                          │  Messages         │
                          │  Voice Models     │
                          │  ...              │
                          └──────────────────┘
```

---

## Security Notes

1. **Never commit `.env` files** — They contain API keys and secrets
2. **Use Render environment variables** for all secrets on cloud
3. **Set `AUTH_REQUIRED=true`** on cloud — don't leave your API open
4. **Set `HTTPS_REQUIRED=true`** — Both Vercel and Render provide free HTTPS
5. **Rotate your `ENCRYPTION_KEY`** if it was ever exposed
6. **Use Neon's connection pooling** — It's enabled by default and handles serverless scaling

---

## Cost Summary

| Service | Plan | Monthly Cost |
|---------|------|-------------|
| GitHub | Free (public) | $0 |
| Render Web Service | Free | $0 |
| Vercel Hobby | Free | $0 |
| Neon PostgreSQL | Free | $0 |
| UptimeRobot | Free | $0 |
| **Total** | | **$0** |

### Paid Upgrade Path (if needed)

| Service | Upgrade | Cost | Benefit |
|---------|---------|------|---------|
| Render | Starter | $7/mo | No cold starts, 1GB RAM |
| Neon | Pro | $19/mo | 10GB storage, no auto-suspend |
| Vercel | Pro | $20/mo | More bandwidth, team features |