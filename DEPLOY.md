# sedr — Production Deployment

Concise guide for deploying the sedr API (Railway) and frontend (Vercel).

## 1. Railway (API backend)

### Prerequisites

- [Railway CLI](https://docs.railway.app/develop/cli) installed
- Google Cloud / provider keys ready (optional — API starts without them)

### Deploy (three commands)

```bash
railway login
railway init          # link this repo, select/create project
railway up            # builds Dockerfile and deploys
```

### Persistent data

In the Railway dashboard for this service:

1. **Volumes** → Add volume → mount path: `/data`
2. Confirm env var `AI_OS_DATA_DIR=/data` (set by Dockerfile default)

Knowledge, memory, and indexes persist under `/data`.

### Required Railway variables

Set in **Variables** (or sync from `.env`):

| Variable | Notes |
|----------|-------|
| `AI_OS_DATA_DIR` | `/data` (default in image) |
| `AI_OS_LOG_LEVEL` | `info` |
| `PORT` | Injected automatically by Railway |

Optional provider keys — add as you connect integrations (see section 4).

### Health check

Railway uses `GET /api/v1/health` (configured in `railway.toml`).

---

## 2. DNS (`api.sedr.ca`)

In your DNS provider (e.g. Cloudflare):

| Type | Name | Value |
|------|------|-------|
| CNAME | `api` | `<your-service>.up.railway.app` |

In Railway → **Settings** → **Networking** → add custom domain `api.sedr.ca`.

Verify:

```bash
curl -s https://api.sedr.ca/api/v1/health
# {"status":"ok","service":"sedr-api"}
```

---

## 3. Vercel (frontend)

Frontend lives in `web/`. Production API URL:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_AI_OS_API_URL` | `https://api.sedr.ca` |

Already in `web/.env.production`. Confirm in Vercel → Project → Settings → Environment Variables.

Deploy:

```bash
cd web && vercel --prod
```

CORS for `https://sedr.ca` and `https://www.sedr.ca` is built into the API.

---

## 4. API keys (optional providers)

The API **never crashes** when optional providers are missing. Configure as needed:

| Provider | Variable(s) |
|----------|-------------|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| GitHub | `GITHUB_TOKEN` |
| Gmail / Calendar / Drive | `GOOGLE_ACCESS_TOKEN`, `GOOGLE_REFRESH_TOKEN` (via `uv run ai-os auth google`) |
| Discord | `DISCORD_BOT_TOKEN` |
| Notion | `NOTION_API_KEY` |
| Slack | `SLACK_BOT_TOKEN` |

Obtain Google tokens locally:

```bash
uv run ai-os auth google
# paste GOOGLE_ACCESS_TOKEN and GOOGLE_REFRESH_TOKEN into Railway variables
```

---

## 5. One-command health check

```bash
curl -fsS https://api.sedr.ca/api/v1/health && \
curl -fsS https://api.sedr.ca/api/v1/providers/health | head -c 500 && echo
```

Local:

```bash
curl -fsS http://127.0.0.1:8741/api/v1/health
```

---

## 6. Disaster recovery

| Scenario | Action |
|----------|--------|
| API won't start | `railway logs` — check missing volume mount or port |
| Data loss | Restore Railway volume snapshot; ensure `/data` is mounted |
| Bad env var | Remove variable in Railway → redeploy |
| Frontend can't reach API | Verify `NEXT_PUBLIC_AI_OS_API_URL`, DNS for `api.sedr.ca`, CORS |
| Google token expired | Re-run `uv run ai-os auth google`, update Railway vars |
| Full redeploy | `railway up` from repo root; `cd web && vercel --prod` |

Startup prints a provider checklist to logs (`railway logs`) — use it to see which integrations need credentials.

---

## Local Docker smoke test

```bash
docker build -t sedr-api .
docker run --rm -p 8741:8741 -e PORT=8741 -v sedr-data:/data sedr-api
curl http://127.0.0.1:8741/api/v1/health
```
