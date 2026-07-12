"""AI-OS API server entry point."""

from __future__ import annotations


def main() -> None:
    import uvicorn

    uvicorn.run(
        "ai_os.api.app:app",
        host="127.0.0.1",
        port=8741,
        reload=False,
    )


if __name__ == "__main__":
    main()
