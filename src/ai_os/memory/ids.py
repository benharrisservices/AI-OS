"""Memory identifier generation."""

from ulid import ULID


def new_memory_id(memory_type: str) -> str:
    prefix = {
        "working": "wmem",
        "episodic": "emem",
        "semantic": "smem",
        "procedural": "pmem",
    }.get(memory_type, "mem")
    return f"{prefix}_{ULID()}"
