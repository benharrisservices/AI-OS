# AI-OS Web Dashboard

Thin Next.js client for the AI-OS platform. All business logic stays in the Python backend.

## Prerequisites

- Node.js 20+
- AI-OS Python environment with API extras: `uv sync --extra api`

## Run

Terminal 1 — API server (from repo root):

```bash
uv run ai-os-api
```

Terminal 2 — Web dashboard:

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Environment

Copy `.env.local` (default points to `http://127.0.0.1:8741`).

## Build

```bash
npm run build
npm start
```
