"""Tests for the shared memory cleanup module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fastshare._cleanup import (
    CleanupResult,
    _discover_candidates,
    _filter_orphans,
    cleanup,
)


class TestCleanupResult:
    """Tests for the CleanupResult dataclass."""

    def test_default_empty(self):
        result = CleanupResult()
        assert result.cleaned == []
        assert result.failed == []
        assert result.skipped == []

    def test_bool_truthiness(self):
        empty = CleanupResult()
        assert not empty.cleaned  # empty list is falsy

        non_empty = CleanupResult(cleaned=["FSHR_a1b2c3d4"])
        assert non_empty.cleaned  # non-empty list is truthy

    def test_repr(self):
        result = CleanupResult(cleaned=["FSHR_abc"], failed=[], skipped=["FSHR_xyz"])
        r = repr(result)
        assert "CleanupResult" in r
        assert "FSHR_abc" in r
        assert "FSHR_xyz" in r


class TestDiscoverCandidates:
    """Tests for _discover_candidates() with mocked platform."""

    @patch("fastshare._cleanup.Path")
    @patch("fastshare._cleanup.sys")
    def test_linux_discovery(self, mock_sys, mock_path_cls):
        mock_sys.platform = "linux"

        # Create mock entries: some with FSHR_ prefix, some without
        fshr_entry1 = MagicMock()
        fshr_entry1.name = "FSHR_a1b2c3d4"
        fshr_entry2 = MagicMock()
        fshr_entry2.name = "FSHR_e5f6g7h8"
        other_entry = MagicMock()
        other_entry.name = "sem.something"
        another_entry = MagicMock()
        another_entry.name = "pulse-shm-12345"

        mock_dev_shm = MagicMock()
        mock_dev_shm.is_dir.return_value = True
        mock_dev_shm.iterdir.return_value = [
            fshr_entry1,
            other_entry,
            fshr_entry2,
            another_entry,
        ]
        mock_path_cls.return_value = mock_dev_shm

        result = _discover_candidates()
        assert result == ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]

    @patch("fastshare._cleanup.sys")
    def test_non_linux_returns_empty(self, mock_sys):
        mock_sys.platform = "win32"
        result = _discover_candidates()
        assert result == []

    @patch("fastshare._cleanup.Path")
    @patch("fastshare._cleanup.sys")
    def test_linux_no_dev_shm(self, mock_sys, mock_path_cls):
        mock_sys.platform = "linux"
        mock_dev_shm = MagicMock()
        mock_dev_shm.is_dir.return_value = False
        mock_path_cls.return_value = mock_dev_shm

        result = _discover_candidates()
        assert result == []


class TestFilterOrphans:
    """Tests for _filter_orphans() orphan/skip partitioning."""

    def test_all_orphans(self):
        """With empty registry, all candidates are orphans."""
        from fastshare._registry import _registry

        # Registry should be empty (autouse fixture cleans it)
        assert len(_registry) == 0
        orphans, skipped = _filter_orphans(["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"])
        assert orphans == ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]
        assert skipped == []

    def test_skips_own_blocks(self):
        """Blocks in the registry should be skipped."""
        from fastshare._registry import _registry

        # Simulate a block in the registry
        _registry["FSHR_a1b2c3d4"] = [MagicMock()]
        try:
            orphans, skipped = _filter_orphans(["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"])
            assert orphans == ["FSHR_e5f6g7h8"]
            assert skipped == ["FSHR_a1b2c3d4"]
        finally:
            _registry.pop("FSHR_a1b2c3d4", None)

    def test_mixed(self):
        """Mix of own blocks and orphans partitions correctly."""
        from fastshare._registry import _registry

        _registry["FSHR_own1"] = [MagicMock()]
        _registry["FSHR_own2"] = [MagicMock()]
        try:
            candidates = ["FSHR_own1", "FSHR_orphan1", "FSHR_own2", "FSHR_orphan2"]
            orphans, skipped = _filter_orphans(candidates)
            assert orphans == ["FSHR_orphan1", "FSHR_orphan2"]
            assert skipped == ["FSHR_own1", "FSHR_own2"]
        finally:
            _registry.pop("FSHR_own1", None)
            _registry.pop("FSHR_own2", None)


class TestCleanup:
    """Tests for the cleanup() main entry point."""

    @patch("fastshare._cleanup._try_unlink")
    @patch("fastshare._cleanup._discover_candidates")
    def test_dry_run_no_unlink(self, mock_discover, mock_unlink):
        mock_discover.return_value = ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]

        result = cleanup(dry_run=True)

        mock_unlink.assert_not_called()
        assert result.cleaned == ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]
        assert result.failed == []
        assert result.skipped == []

    @patch("fastshare._cleanup._try_unlink")
    @patch("fastshare._cleanup._discover_candidates")
    def test_cleanup_unlinks_orphans(self, mock_discover, mock_unlink):
        mock_discover.return_value = ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]
        mock_unlink.return_value = (True, "")

        result = cleanup(dry_run=False)

        assert mock_unlink.call_count == 2
        assert result.cleaned == ["FSHR_a1b2c3d4", "FSHR_e5f6g7h8"]
        assert result.failed == []

    @patch("fastshare._cleanup._try_unlink")
    @patch("fastshare._cleanup._discover_candidates")
    def test_cleanup_collects_failures(self, mock_discover, mock_unlink):
        mock_discover.return_value = ["FSHR_a1b2c3d4", "FSHR_failblock"]
        mock_unlink.side_effect = [
            (True, ""),
            (False, "Permission denied"),
        ]

        result = cleanup(dry_run=False)

        assert result.cleaned == ["FSHR_a1b2c3d4"]
        assert result.failed == [("FSHR_failblock", "Permission denied")]

    @patch("fastshare._cleanup._try_unlink")
    @patch("fastshare._cleanup._discover_candidates")
    def test_cleanup_skips_own_blocks(self, mock_discover, mock_unlink):
        from fastshare._registry import _registry

        _registry["FSHR_myblock"] = [MagicMock()]
        try:
            mock_discover.return_value = ["FSHR_myblock", "FSHR_orphan"]
            mock_unlink.return_value = (True, "")

            result = cleanup(dry_run=False)

            # _try_unlink should only be called for the orphan, not our own block
            mock_unlink.assert_called_once_with("FSHR_orphan")
            assert result.cleaned == ["FSHR_orphan"]
            assert result.skipped == ["FSHR_myblock"]
        finally:
            _registry.pop("FSHR_myblock", None)

    @patch("fastshare._cleanup._discover_candidates")
    def test_empty_discovery(self, mock_discover):
        mock_discover.return_value = []

        result = cleanup(dry_run=False)

        assert result.cleaned == []
        assert result.failed == []
        assert result.skipped == []
