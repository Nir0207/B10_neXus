"""
Tests for idempotency.py

Covers:
- New file not in manifest → is_already_processed returns False
- After mark_processed → is_already_processed returns True
- Modifying file content invalidates the manifest entry
- filter_unprocessed returns only files with changed/new hashes
- Manifest is persisted to disk and survives a reload
"""
from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

import idempotency


class TestIdempotency:
    def setup_method(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.manifest_path = self.tmp / ".manifest.json"
        self._patcher = patch.object(idempotency, "MANIFEST_PATH", self.manifest_path)
        self._patcher.start()

    def teardown_method(self) -> None:
        self._patcher.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ── is_already_processed ─────────────────────────────────────────────────

    def test_new_file_returns_false(self) -> None:
        f = self.tmp / "a.json"
        f.write_text('{"x": 1}')
        assert not idempotency.is_already_processed(f)

    def test_after_mark_processed_returns_true(self) -> None:
        f = self.tmp / "a.json"
        f.write_text('{"x": 1}')
        idempotency.mark_processed(f)
        assert idempotency.is_already_processed(f)

    def test_modified_content_returns_false(self) -> None:
        f = self.tmp / "a.json"
        f.write_text('{"x": 1}')
        idempotency.mark_processed(f)
        f.write_text('{"x": 2}')  # mutate content
        assert not idempotency.is_already_processed(f)

    def test_different_files_tracked_independently(self) -> None:
        f1 = self.tmp / "one.json"
        f2 = self.tmp / "two.json"
        f1.write_text('{"a": 1}')
        f2.write_text('{"b": 2}')
        idempotency.mark_processed(f1)
        assert idempotency.is_already_processed(f1)
        assert not idempotency.is_already_processed(f2)

    def test_mark_processed_many_tracks_all_files(self) -> None:
        f1 = self.tmp / "one.json"
        f2 = self.tmp / "two.json"
        f1.write_text('{"a": 1}')
        f2.write_text('{"b": 2}')
        idempotency.mark_processed_many([f1, f2])
        assert idempotency.is_already_processed(f1)
        assert idempotency.is_already_processed(f2)

    # ── filter_unprocessed ───────────────────────────────────────────────────

    def test_filter_returns_only_unprocessed(self) -> None:
        f1 = self.tmp / "f1.json"
        f2 = self.tmp / "f2.json"
        f1.write_text('{"a": 1}')
        f2.write_text('{"b": 2}')
        idempotency.mark_processed(f1)
        result = idempotency.filter_unprocessed([f1, f2])
        assert f1 not in result
        assert f2 in result

    def test_filter_empty_list_returns_empty(self) -> None:
        assert idempotency.filter_unprocessed([]) == []

    def test_filter_all_processed_returns_empty(self) -> None:
        f = self.tmp / "done.json"
        f.write_text('{"z": 99}')
        idempotency.mark_processed(f)
        assert idempotency.filter_unprocessed([f]) == []

    # ── persistence ──────────────────────────────────────────────────────────

    def test_manifest_written_to_disk(self) -> None:
        f = self.tmp / "p.json"
        f.write_text('{"data": 1}')
        idempotency.mark_processed(f)
        assert self.manifest_path.exists()

    def test_manifest_content_is_valid_json(self) -> None:
        f = self.tmp / "p.json"
        f.write_text('{"data": 1}')
        idempotency.mark_processed(f)
        data = json.loads(self.manifest_path.read_text())
        assert str(f) in data

    def test_missing_manifest_returns_empty_dict(self) -> None:
        assert not self.manifest_path.exists()
        manifest = idempotency.load_manifest()
        assert manifest == {}

    def test_manifest_survives_reload(self) -> None:
        f = self.tmp / "reload.json"
        f.write_text('{"reload": true}')
        idempotency.mark_processed(f)
        # Reload without the in-memory cache
        reloaded = idempotency.load_manifest()
        assert str(f) in reloaded
