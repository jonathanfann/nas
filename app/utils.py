"""Utility functions for the NAS file server."""

import os
import time
from datetime import datetime
from pathlib import Path

_base = os.environ.get("NAS_BASE_PATH")
if not _base:
    raise ValueError(
        "NAS_BASE_PATH must be set. Copy .env.example to .env and configure."
    )
BASE_PATH = Path(_base)

# Media type buckets: extension -> bucket name
MEDIA_EXTENSIONS = {
    "images": {
        "jpg",
        "jpeg",
        "png",
        "gif",
        "webp",
        "svg",
        "bmp",
        "ico",
        "tiff",
        "tif",
        "heic",
        "heif",
        "avif",
        "raw",
        "cr2",
        "nef",
        "arw",
    },
    "videos": {
        "mp4",
        "mkv",
        "webm",
        "mov",
        "avi",
        "wmv",
        "flv",
        "m4v",
        "mpeg",
        "mpg",
        "3gp",
        "ogv",
        "ts",
        "m2ts",
    },
    "music": {
        "mp3",
        "flac",
        "wav",
        "ogg",
        "m4a",
        "aac",
        "wma",
        "opus",
        "aiff",
        "aif",
    },
}
# Flatten to single dict for lookup
_EXT_TO_BUCKET = {}
for bucket, exts in MEDIA_EXTENSIONS.items():
    for ext in exts:
        _EXT_TO_BUCKET[ext] = bucket

BUCKET_NAMES = ["images", "videos", "music", "files"]

# Cache for bucket counts: {bucket: count}, expires after CACHE_TTL seconds
_bucket_count_cache = {}
_bucket_count_cache_time = 0
CACHE_TTL = 300  # 5 minutes


def get_media_type(path: Path) -> str:
    """Return bucket name for a file: images, videos, music, or files."""
    ext = path.suffix.lstrip(".").lower()
    return _EXT_TO_BUCKET.get(ext, "files")


def get_relative_path(path_str: str) -> Path:
    """Resolve path and ensure it's within BASE_PATH (prevent path traversal)."""
    if not path_str or path_str == ".":
        return BASE_PATH
    path = (BASE_PATH / path_str).resolve()
    if not str(path).startswith(str(BASE_PATH.resolve())):
        return BASE_PATH
    return path


def format_mtime(mtime: float) -> str:
    """Format Unix mtime for display."""
    return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")


def format_size(size: int) -> str:
    """Format byte size for display."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def _walk_files():
    """Walk BASE_PATH and yield (path, name, rel_path, size, bucket, mtime) for each file."""
    for root, dirs, files in os.walk(BASE_PATH, topdown=True):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        root_path = Path(root)
        for name in files:
            if name.startswith("."):
                continue
            path = root_path / name
            try:
                stat = path.stat()
                rel = str(path.relative_to(BASE_PATH))
                bucket = get_media_type(path)
                yield path, name, rel, stat.st_size, bucket, stat.st_mtime
            except (OSError, ValueError):
                continue


def get_bucket_counts() -> dict[str, int]:
    """Return cached counts per bucket. Refreshes after CACHE_TTL."""
    global _bucket_count_cache, _bucket_count_cache_time
    now = time.time()
    if now - _bucket_count_cache_time < CACHE_TTL and _bucket_count_cache:
        return _bucket_count_cache
    counts = {b: 0 for b in BUCKET_NAMES}
    for _, _, _, _, bucket, _ in _walk_files():
        counts[bucket] = counts.get(bucket, 0) + 1
    _bucket_count_cache = counts
    _bucket_count_cache_time = now
    return counts


def list_files_by_bucket(
    bucket: str,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """List files in a bucket. Returns (entries, total_count)."""
    if bucket not in BUCKET_NAMES:
        return [], 0
    matches = []
    for _, name, rel_path, size, b, mtime in _walk_files():
        if b == bucket:
            matches.append(
                {
                    "name": name,
                    "path": rel_path,
                    "size_str": format_size(size),
                    "bucket": b,
                    "mtime_str": format_mtime(mtime),
                }
            )
    total = len(matches)
    start = (page - 1) * per_page
    end = start + per_page
    return matches[start:end], total


def search_files(
    q: str,
    bucket_filter: str | None = None,
    page: int = 1,
    per_page: int = 50,
) -> tuple[list[dict], int]:
    """Search files by name. Returns (entries, total_count)."""
    q_lower = (q or "").strip().lower()
    if not q_lower:
        return [], 0

    matches = []
    for _, name, rel_path, size, bucket, mtime in _walk_files():
        if bucket_filter and bucket != bucket_filter:
            continue
        if q_lower in name.lower():
            matches.append(
                {
                    "name": name,
                    "path": rel_path,
                    "size_str": format_size(size),
                    "bucket": bucket,
                    "mtime_str": format_mtime(mtime),
                }
            )

    total = len(matches)
    start = (page - 1) * per_page
    end = start + per_page
    page_entries = matches[start:end]

    return page_entries, total
