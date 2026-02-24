"""Programmatic cleanup of orphaned FSHR-prefixed shared memory blocks."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fastshare._platform import _FSHR_PREFIX, _attach_shm
from fastshare._registry import _registry

logger = logging.getLogger("fastshare")


@dataclass
class CleanupResult:
    """Result of a cleanup operation.

    Attributes:
        cleaned: Block names successfully unlinked.
        failed: Tuples of (block_name, error_message) for blocks that could not be cleaned.
        skipped: Block names skipped (in calling process's registry).
    """

    cleaned: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _discover_candidates() -> list[str]:
    """Discover FSHR-prefixed shared memory block names on the system.

    Linux: scans /dev/shm for files matching the FSHR_ prefix.
    macOS/Windows: no filesystem-based discovery available; returns empty list.
    """
    if sys.platform == "linux":
        dev_shm = Path("/dev/shm")
        if dev_shm.is_dir():
            return [
                f.name
                for f in dev_shm.iterdir()
                if f.name.startswith(_FSHR_PREFIX)
            ]
    # macOS: no /dev/shm equivalent; POSIX shm objects are kernel-only
    # Windows: named file mappings cannot be enumerated via standard APIs
    return []


def _filter_orphans(candidates: list[str]) -> tuple[list[str], list[str]]:
    """Separate candidates into orphans and skipped (own blocks).

    Args:
        candidates: List of FSHR-prefixed block names discovered on the system.

    Returns:
        (orphans, skipped) -- orphans to clean, skipped because in our registry.
    """
    own_names = set(_registry.keys())
    orphans = [name for name in candidates if name not in own_names]
    skipped = [name for name in candidates if name in own_names]
    return orphans, skipped


def _try_unlink(name: str) -> tuple[bool, str]:
    """Attempt to unlink a shared memory block by name.

    Uses _attach_shm() for tracker-safe attach (avoids resource tracker
    interference on Python < 3.13).

    Args:
        name: The FSHR-prefixed block name to unlink.

    Returns:
        (success, error_message) -- success=True if unlinked or already gone,
        error_message is empty on success.
    """
    try:
        shm = _attach_shm(name)
        shm.close()
        shm.unlink()
        return True, ""
    except FileNotFoundError:
        # Block already gone -- treat as success
        return True, ""
    except PermissionError as e:
        return False, str(e)
    except OSError as e:
        return False, str(e)


def cleanup(dry_run: bool = False) -> CleanupResult:
    """Clean up orphaned FSHR-prefixed shared memory blocks.

    Discovers all FSHR-prefixed shared memory blocks on the system, filters out
    blocks owned by the calling process, and unlinks the rest.

    Args:
        dry_run: If True, discover and report orphaned blocks without unlinking them.

    Returns:
        CleanupResult with cleaned, failed, and skipped lists.
    """
    candidates = _discover_candidates()
    orphans, skipped = _filter_orphans(candidates)

    if dry_run:
        logger.info("Dry run: found %d orphaned block(s)", len(orphans))
        return CleanupResult(cleaned=orphans, failed=[], skipped=skipped)

    cleaned: list[str] = []
    failed: list[tuple[str, str]] = []

    for name in orphans:
        success, error = _try_unlink(name)
        if success:
            cleaned.append(name)
            logger.debug("Cleaned orphaned block %s", name)
        else:
            failed.append((name, error))
            logger.warning("Failed to clean block %s: %s", name, error)

    logger.info(
        "Cleanup complete: %d cleaned, %d failed, %d skipped",
        len(cleaned),
        len(failed),
        len(skipped),
    )
    return CleanupResult(cleaned=cleaned, failed=failed, skipped=skipped)
