"""FastAPI application — thin HTTP layer over AI-OS."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_os.api.routers import (
    automations,
    dashboard,
    decisions,
    imports,
    knowledge,
    memory,
    models,
    providers,
    search,
    settings,
    workflows,
)

app = FastAPI(
    title="AI-OS API",
    description="Thin HTTP wrapper over existing AI-OS services",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(memory.router, prefix="/api/v1")
app.include_router(decisions.router, prefix="/api/v1")
app.include_router(workflows.router, prefix="/api/v1")
app.include_router(automations.router, prefix="/api/v1")
app.include_router(providers.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(settings.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(imports.router, prefix="/api/v1")


@app.get("/api/v1/health")
def health() -> dict:
    return {"status": "ok", "service": "ai-os-api"}
