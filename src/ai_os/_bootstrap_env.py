"""Load .env exactly once at interpreter startup (invoked from ai_os_bootstrap.pth)."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()
