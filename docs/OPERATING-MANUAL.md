# AI-OS Operating Manual

A plain-language guide to installing, configuring, and using AI-OS every day. No programming experience required.

---

## What is AI-OS?

AI-OS is a personal assistant system on your computer. It helps you:

- **Store and search** your documents, notes, and files
- **Run daily routines** like morning briefings and end-of-day reviews
- **Make structured decisions** using your own knowledge
- **Connect** to services like GitHub, email, and calendar (optional)

Everything stays on your machine. Your secrets never go into the project folder.

---

## Part 1 — Installation

### What you need

- A Mac or Linux computer
- Internet access (for setup and optional cloud features)
- About 15 minutes for first setup

### Step 1: Install AI-OS

Open **Terminal** (Mac: search “Terminal” in Spotlight).

```bash
cd /path/to/AI-OS
./scripts/install.sh
```

This installs required software and creates folders automatically.

### Step 2: Install Ollama (your local AI engine)

1. Go to [ollama.com](https://ollama.com) and download the app
2. Open Terminal and run:

```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

`nomic-embed-text` powers search. `llama3.2` powers local chat.

### Step 3: First-run setup

```bash
uv run ai-os setup
```

Read each line. Green checkmarks mean OK. If something fails, the message tells you exactly what to do next.

### Step 4: Create your configuration file

```bash
cp .env.example .env
```

Open `.env` in any text editor. Add your API keys (see Part 3). **Never share this file.**

---

## Part 2 — Importing your knowledge

AI-OS learns from your files. Nothing is imported without your explicit command.

### See the recommended order

```bash
uv run ai-os onboarding
```

This shows 12 categories in the best order (AI-OS docs first, then projects, then notes, etc.).

### Validate before importing

Replace `./docs` with your actual folder path:

```bash
uv run ai-os onboarding validate ai-os-repo ./docs
```

You will see:
- How many files were found
- How many are new vs already imported
- Estimated time
- Any errors

### Import when ready

```bash
uv run ai-os onboarding import ai-os-repo ./docs --yes
```

The `--yes` flag means you confirmed you want to proceed.

### Import categories

| When ready | Command pattern |
|------------|-----------------|
| AI-OS docs | `ai-os onboarding import ai-os-repo ./docs --yes` |
| A project folder | `ai-os onboarding import business-projects ~/Projects/MyClient --yes` |
| University files | `ai-os onboarding import university ~/University --yes` |
| PDF folder | `ai-os onboarding import pdfs ~/Documents/PDFs --yes` |
| Chat exports | `ai-os onboarding import exported-chats ~/Exports/chat.json --yes` |
| Travel notes | `ai-os onboarding import travel-folders ~/Travel --yes` |

### Check your knowledge

```bash
uv run ai-os search "your topic"
uv run ai-os status
```

---

## Part 3 — Connecting providers (optional)

Providers connect AI-OS to external services. Only configure what you use.

Copy the template for reference:

```bash
cat config/personal/providers.env.example
```

Full instructions: `docs/personal/provider-configuration.md`

### Minimum (free, local)

| Service | What to do |
|---------|------------|
| Ollama | Install + `ollama pull nomic-embed-text` |

### Recommended

| Service | Get credentials from |
|---------|---------------------|
| GitHub | github.com → Settings → Developer settings → Tokens |
| OpenAI | platform.openai.com → API keys |
| Anthropic | console.anthropic.com → API keys |

### Google (Gmail, Calendar, Drive)

Requires a Google Cloud project and OAuth token. See `docs/personal/provider-configuration.md` for step-by-step instructions.

### Verify connections

```bash
uv run ai-os provider health
```

---

## Part 4 — Running workflows

Workflows are pre-built routines. Each produces a file in your `memory/` folder.

### Morning Briefing

1. Open `config/personal/workflows/morning-briefing.json` in a text editor
2. Edit the `focus` field to describe what matters today
3. Run:

```bash
uv run ai-os workflow run morning-briefing \
  --input-file config/personal/workflows/morning-briefing.json
```

Output: `memory/briefings/morning-YYYY-MM-DD.md`

### Daily Review (evening)

```bash
uv run ai-os workflow run daily-review \
  --input-file config/personal/workflows/daily-review.json
```

### Weekly Review

```bash
uv run ai-os workflow run weekly-review \
  --input-file config/personal/workflows/weekly-review.json
```

### Other workflows

| Workflow | Example config |
|----------|----------------|
| Travel Planning | `config/personal/workflows/travel-planning.json` |
| Research | `config/personal/workflows/research-pipeline.json` |
| Project Review | `config/personal/workflows/project-review.json` |

### If a workflow fails

```bash
uv run ai-os task logs TASK_ID
```

The task ID is shown when the workflow finishes.

---

## Part 5 — Daily routine

### Morning (5 minutes)

```bash
uv run ai-os setup          # quick check (optional after first week)
uv run ai-os dashboard      # overview
uv run ai-os workflow run morning-briefing -f config/personal/workflows/morning-briefing.json
```

Read the briefing file in `memory/briefings/`.

### During the day

- Drop new files into `knowledge/raw/inbox/` for automatic pickup:

```bash
uv run ai-os watch --once
```

- Search when you need context:

```bash
uv run ai-os search "client contract terms"
```

### Evening (5 minutes)

```bash
uv run ai-os workflow run daily-review -f config/personal/workflows/daily-review.json
```

---

## Part 6 — Weekly maintenance

Every Friday or Sunday:

```bash
uv run ai-os workflow run weekly-review -f config/personal/workflows/weekly-review.json
uv run ai-os doctor
uv run ai-os backup
```

Once a month:

```bash
uv run ai-os maintenance run
uv run ai-os doctor --full
```

---

## Part 7 — Troubleshooting

### “Ollama is not running”

```bash
ollama serve
ollama pull nomic-embed-text
```

### “Setup incomplete”

```bash
uv run ai-os setup
```

Follow the arrow (→) instructions on each failed line.

### Search returns nothing

1. Check documents were imported: `uv run ai-os status`
2. Re-import if needed: `uv run ai-os onboarding import markdown-notes ~/Notes --yes`

### Provider shows “not configured”

That provider is optional. Add the API key to `.env` if you need it.

### Workflow wrote a file with `{{MISSING:...}}` in the name

Update your workflow JSON to use paths like `./memory/briefings/morning-{{date}}.md` and run again.

### Something else is wrong

```bash
uv run ai-os doctor --full
uv run ai-os diagnostics
```

---

## Part 8 — Backup and restore

### Create a backup

```bash
uv run ai-os backup
```

Backups are saved automatically in your knowledge backup folder.

### Before a large import

Always backup first:

```bash
uv run ai-os backup
uv run ai-os onboarding import business-projects ~/Projects --yes
```

### Restore

Contact your technical support or see `docs/production-readiness.md` for restore procedures. Backups are standard `.tar.gz` archives of your knowledge folders.

---

## Quick reference card

| I want to… | Command |
|------------|---------|
| First-time setup | `ai-os setup` |
| See import plan | `ai-os onboarding` |
| Validate import | `ai-os onboarding validate PRESET PATH` |
| Import files | `ai-os onboarding import PRESET PATH --yes` |
| Search knowledge | `ai-os search "query"` |
| Morning briefing | `ai-os workflow run morning-briefing -f config/personal/workflows/morning-briefing.json` |
| System overview | `ai-os dashboard` |
| Full health check | `ai-os doctor --full` |
| Backup | `ai-os backup` |

---

## Getting help

- Setup guide: `docs/personal/provider-configuration.md`
- Import plan: `docs/personal/knowledge-import-plan.md`
- Workflow templates: `config/personal/workflows/README.md`
