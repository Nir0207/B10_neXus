"""
File-level idempotency guard.

Each raw JSON file is fingerprinted by its MD5 hash.  A JSON manifest
persisted on disk records every successfully processed file.  Re-running
the pipeline skips files whose content has not changed, ensuring writes to
Postgres and Neo4j are never duplicated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from config import MANIFEST_PATH


def _file_md5(path: Path) -> str:
    hasher = hashlib.md5()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_manifest() -> dict[str, str]:
    """Return {absolute_path_str: md5_hex} for all previously processed files."""
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict[str, str]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MANIFEST_PATH.with_name(f"{MANIFEST_PATH.name}.tmp")
    tmp_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp_path.replace(MANIFEST_PATH)


def is_already_processed(path: Path) -> bool:
    """True iff *path* exists in the manifest with an identical hash."""
    return load_manifest().get(str(path)) == _file_md5(path)


def mark_processed(path: Path) -> None:
    """Record *path* as successfully processed in the manifest."""
    mark_processed_many([path])


def mark_processed_many(paths: Iterable[Path]) -> None:
    """Record *paths* as successfully processed in one manifest write."""
    manifest = load_manifest()
    for path in paths:
        manifest[str(path)] = _file_md5(path)
    save_manifest(manifest)


def filter_unprocessed(paths: list[Path]) -> list[Path]:
    """Return only paths whose content hash differs from the stored manifest."""
    manifest = load_manifest()
    return [p for p in paths if manifest.get(str(p)) != _file_md5(p)]
