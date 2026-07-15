"""API authentication for write endpoints.

When AI_OS_API_KEY is set (production), upload and other write routes require
``X-API-Key`` or ``Authorization: Bearer <key>``. When unset (local development),
authentication is not enforced. Health and other read routes stay public.
"""

from __future__ import annotations

import os
import secrets

from fastapi import Header, HTTPException, status

API_KEY_ENV = "AI_OS_API_KEY"


def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> None:
    expected = os.environ.get(API_KEY_ENV, "").strip()
    if not expected:
        return

    provided = (x_api_key or "").strip()
    if not provided and authorization:
        auth = authorization.strip()
        if auth.lower().startswith("bearer "):
            provided = auth[7:].strip()

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized — provide a valid X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
