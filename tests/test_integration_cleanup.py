"""Cleanup tool cross-process integration tests.

Tests that cleanup() discovers and unlinks orphaned FSHR-prefixed shared memory
blocks, and that dry_run mode reports without unlinking.

These tests only work on Linux where /dev/shm scanning is available.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        sys.platform != "linux",
        reason="cleanup discovery requires /dev/shm (Linux only)",
    ),
]


def test_cleanup_discovers_orphaned_blocks():
    """cleanup() discovers and unlinks an orphaned FSHR block on Linux."""
    from fastshare._platform import _create_shm
    from fastshare import cleanup

    # Create a raw shared memory block with FSHR_ prefix but do NOT
    # register it in fastshare's registry -- simulating an orphan.
    shm = _create_shm("FSHR_TESTORPHN", 1024)
    shm.close()  # Close our local handle but don't unlink

    try:
        result = cleanup()
        assert "FSHR_TESTORPHN" in result.cleaned, (
            f"Orphan not found in cleaned list: {result.cleaned}"
        )
    finally:
        # Safety net: try to unlink if cleanup didn't get it
        try:
            from multiprocessing.shared_memory import SharedMemory

            s = SharedMemory("FSHR_TESTORPHN", create=False)
            s.close()
            s.unlink()
        except FileNotFoundError:
            pass  # Already cleaned up -- expected


def test_cleanup_dry_run():
    """cleanup(dry_run=True) reports orphans without unlinking them."""
    from multiprocessing.shared_memory import SharedMemory

    from fastshare._platform import _create_shm
    from fastshare import cleanup

    # Create orphan block
    shm = _create_shm("FSHR_TESTDRYRN", 1024)
    shm.close()

    try:
        result = cleanup(dry_run=True)
        assert "FSHR_TESTDRYRN" in result.cleaned, (
            f"Orphan not reported in dry_run: {result.cleaned}"
        )

        # Verify block still exists (not actually unlinked)
        still_there = SharedMemory("FSHR_TESTDRYRN", create=False)
        still_there.close()
        still_there.unlink()  # Manual cleanup
    except Exception:
        # Safety: clean up the block no matter what
        try:
            s = SharedMemory("FSHR_TESTDRYRN", create=False)
            s.close()
            s.unlink()
        except FileNotFoundError:
            pass
        raise
