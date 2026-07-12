# Provider Configuration Guide

Step-by-step setup for the nine priority AI-OS providers. All values below are **examples** — never commit real credentials.

Template file: [`config/personal/providers.env.example`](../../config/personal/providers.env.example)

## Validation commands

```bash
ai-os provider health          # per-provider status
ai-os provider list            # capabilities
ai-os doctor --full            # system-wide check
```

---

## 1. Ollama (local LLM + embeddings)

**Purpose:** Default local inference and knowledge embeddings. No API key required.

**What you need:**
- [Ollama](https://ollama.com) installed and running
- Models pulled locally

**Setup:**

```bash
ollama serve                          # if not already running
ollama pull llama3.2                  # chat model
ollama pull nomic-embed-text          # embedding model (required for knowledge search)
```

**`.env` values:**

```env
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_DEFAULT_MODEL=llama3.2
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
```

**Verify:** `ai-os provider health` → `ollama: healthy`

---

## 2. GitHub

**Purpose:** Repository analysis, issues, PRs, repo health workflows.

**What you need:**
- GitHub account
- Personal Access Token (PAT)

**How to obtain:**
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. **Fine-grained token** (recommended): select repositories you use daily; permissions: `Contents: Read`, `Issues: Read`, `Pull requests: Read`, `Metadata: Read`
3. **Classic token** (simpler): scope `repo` (private repos) or `public_repo` only

**`.env` values:**

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify:** `ai-os provider health` → `github: healthy`

**Invoke example:**

```bash
# Via provider (programmatic)
ai-os provider list   # shows repos capability
```

---

## 3. Gmail

**Purpose:** Read profile and message list for morning briefing and inbox workflows.

**What you need:**
- Google account
- Google Cloud project with Gmail API enabled
- OAuth 2.0 credentials
- Access token (short-lived) or refresh token (long-term — v1.2)

**How to obtain:**

1. [Google Cloud Console](https://console.cloud.google.com/) → create or select a project
2. **APIs & Services → Library** → enable **Gmail API**
3. **OAuth consent screen** → External → add your email as a test user
4. **Credentials → Create Credentials → OAuth client ID** → Desktop app
5. Run OAuth flow to obtain tokens:

```bash
# Manual one-time (use Google's OAuth Playground or a local script)
# Scope required: https://www.googleapis.com/auth/gmail.readonly
```

6. Copy the **access token** into `.env` (expires in ~1 hour) or store refresh token for automation (planned v1.2)

**`.env` values:**

```env
GOOGLE_ACCESS_TOKEN=ya29.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GMAIL_CLIENT_ID=123456789012-xxxxxxxx.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
```

**Note:** `GOOGLE_ACCESS_TOKEN` is shared across Gmail, Calendar, and Drive in AI-OS.

**Verify:** `ai-os provider health` → `gmail: healthy`

---

## 4. Google Calendar

**Purpose:** Event listing for morning briefing and meeting preparation.

**What you need:** Same Google Cloud project; enable **Google Calendar API**.

**OAuth scope:** `https://www.googleapis.com/auth/calendar.readonly`

**`.env` values:** Same `GOOGLE_ACCESS_TOKEN` as Gmail. Optionally set:

```env
GOOGLE_CALENDAR_CLIENT_ID=123456789012-xxxxxxxx.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify:** `ai-os provider health` → `google-calendar: healthy`

---

## 5. Google Drive

**Purpose:** File listing and document access for knowledge import.

**What you need:** Same Google Cloud project; enable **Google Drive API**.

**OAuth scope:** `https://www.googleapis.com/auth/drive.readonly`

**`.env` values:** Same `GOOGLE_ACCESS_TOKEN`. Optionally:

```env
GOOGLE_DRIVE_CLIENT_ID=123456789012-xxxxxxxx.apps.googleusercontent.com
GOOGLE_DRIVE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify:** `ai-os provider health` → `google-drive: healthy`

---

## 6. OpenAI

**Purpose:** Cloud LLM fallback when Ollama is unavailable; high-quality reasoning.

**What you need:**
- OpenAI account with billing enabled
- API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

**`.env` values:**

```env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_DEFAULT_MODEL=gpt-4o
```

**Verify:** `ai-os provider health` → `openai: healthy`

---

## 7. Anthropic

**Purpose:** Strong reasoning and long-context tasks.

**What you need:**
- Anthropic account
- API key from [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

**`.env` values:**

```env
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_DEFAULT_MODEL=claude-sonnet-4-20250514
```

**Verify:** `ai-os provider health` → `anthropic: healthy`

---

## 8. Gemini

**Purpose:** Multimodal and long-context cloud model. **Separate from Google Workspace OAuth** — uses AI Studio API key.

**What you need:**
- API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

**`.env` values:**

```env
GOOGLE_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_DEFAULT_MODEL=gemini-2.0-flash
```

**Verify:** `ai-os provider health` → `gemini: healthy`

---

## 9. OpenRouter

**Purpose:** Multi-model gateway; access models without individual provider accounts.

**What you need:**
- Account at [openrouter.ai](https://openrouter.ai)
- API key from [openrouter.ai/keys](https://openrouter.ai/keys)

**`.env` values:**

```env
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Verify:** `ai-os provider health` → `openrouter: healthy`

---

## Recommended configuration order

Configure in this order to maximize daily utility with minimum setup friction:

| Order | Provider | Why first |
|-------|----------|-----------|
| 1 | Ollama | Local, free, powers embeddings + default routing |
| 2 | GitHub | Repo health, AI-OS development, project review |
| 3 | OpenAI or Anthropic | One reliable cloud fallback |
| 4 | OpenRouter | Optional multi-model access |
| 5 | Gemini | Optional; separate API key |
| 6–8 | Gmail, Calendar, Drive | Requires OAuth setup; enable when briefing workflows need live data |

## Routing defaults

After providers are configured:

```env
MODEL_ROUTER_DEFAULT_PROVIDER=ollama
MODEL_ROUTER_FALLBACK_CHAIN=ollama,openai,anthropic,gemini,openrouter
MODEL_ROUTER_PREFER_LOCAL=true
```

Test routing:

```bash
ai-os model route --task "daily review"
```

## Security checklist

- [ ] `.env` is gitignored (never commit)
- [ ] Use fine-grained GitHub tokens with minimum scopes
- [ ] Rotate API keys periodically
- [ ] Google OAuth: use test-user mode until app is verified
- [ ] Run `ai-os config-show` to confirm no secrets appear in committed files
