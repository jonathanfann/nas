"""Utility functions for the NAS file server."""

import os
from pathlib import Path

_base = os.environ.get("NAS_BASE_PATH")
if not _base:
    raise ValueError(
        "NAS_BASE_PATH must be set. Copy .env.example to .env and configure."
    )
BASE_PATH = Path(_base)


def get_relative_path(path_str: str) -> Path:
    """Resolve path and ensure it's within BASE_PATH (prevent path traversal)."""
    if not path_str or path_str == ".":
        return BASE_PATH
    path = (BASE_PATH / path_str).resolve()
    if not str(path).startswith(str(BASE_PATH.resolve())):
        return BASE_PATH
    return path


def format_size(size: int) -> str:
    """Format byte size for display."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"
