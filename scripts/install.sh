#!/usr/bin/env bash
# AI-OS installation script
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> AI-OS Installation"
echo "    Root: $ROOT"

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required (>= 3.12)" >&2
  exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
  echo "ERROR: Python 3.12+ required (found $PY_VERSION)" >&2
  exit 1
fi
echo "    Python: $PY_VERSION"

# Install uv if missing
if ! command -v uv &>/dev/null; then
  echo "==> Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "==> Syncing dependencies..."
uv sync

echo "==> Creating directories..."
mkdir -p knowledge/raw knowledge/processed knowledge/index knowledge/backups
mkdir -p memory/working memory/episodic memory/semantic memory/procedural
mkdir -p memory/agent/tasks memory/agent/logs memory/automation/history memory/automation/state
mkdir -p memory/decisions memory/briefings memory/reviews memory/research memory/meetings memory/travel memory/reports memory/digests memory/inbox

if [ ! -f .env ] && [ -f .env.example ]; then
  echo "==> Creating .env from .env.example..."
  cp .env.example .env
  echo "    Edit .env to add API keys"
fi

echo "==> Running first-run setup..."
uv run ai-os setup || true

echo ""
echo "==> Installation complete"
echo ""
echo "    All commands use:  uv run ai-os <command>"
echo "    Or activate venv:  source .venv/bin/activate   then:  ai-os <command>"
echo ""
echo "    Next steps:"
echo "      1. Install Ollama: https://ollama.com"
echo "      2. ollama pull nomic-embed-text"
echo "      3. uv run ai-os onboarding"
echo "      4. uv run ai-os onboarding import ai-os-repo ./docs --yes"
