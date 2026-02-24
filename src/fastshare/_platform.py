"""Shared memory platform abstraction with FSHR naming and resource tracker bypass."""

from __future__ import annotations

import logging
import secrets
import sys
from multiprocessing import shared_memory

from fastshare._errors import AllocationError, BlockNotFoundError

logger = logging.getLogger("fastshare")

# Platform detection
_POSIX = sys.platform != "win32"
_HAS_TRACK = sys.version_info >= (3, 13)

# FSHR block naming constants
_SHM_SAFE_NAME_LENGTH = 14  # BSD limit (FreeBSD, macOS) -- includes leading '/' on POSIX
_FSHR_PREFIX = "FSHR_"  # 5 chars, leaves room for 8 hex chars
_MAX_RETRIES = 3  # retry on name collision

# One-time warning flag for 3.10-3.12 resource tracker workaround
_warned_tracker = False


def _make_block_name() -> str:
    """Generate a unique FSHR-prefixed block name within BSD limits.

    On POSIX, CPython internally prepends '/' to the name for shm_open().
    The internal POSIX name will be '/FSHR_XXXXXXXX' (14 chars, at limit).
    The user-visible name is 'FSHR_XXXXXXXX' (13 chars).

    Returns:
        Name string without leading slash (CPython adds it internally).
    """
    nbytes = (_SHM_SAFE_NAME_LENGTH - len("/" + _FSHR_PREFIX)) // 2  # = 4 bytes = 8 hex chars
    name = _FSHR_PREFIX + secrets.token_hex(nbytes)  # e.g., "FSHR_a1b2c3d4"
    return name


def _create_shm(name: str, size: int) -> shared_memory.SharedMemory:
    """Create a SharedMemory block with the stdlib resource tracker bypassed.

    On Python 3.13+, uses the native ``track=False`` parameter.
    On Python 3.10-3.12 POSIX, calls ``resource_tracker.unregister()`` after creation.
    On Windows, no resource tracker bypass is needed (OS handles cleanup).

    Args:
        name: Block name (without leading slash).
        size: Size in bytes.

    Returns:
        The created SharedMemory object.

    Raises:
        FileExistsError: If a block with this name already exists (caller handles retry).
    """
    global _warned_tracker  # noqa: PLW0603

    if _HAS_TRACK:
        shm = shared_memory.SharedMemory(name=name, create=True, size=size, track=False)
    else:
        shm = shared_memory.SharedMemory(name=name, create=True, size=size)
        if _POSIX:
            from multiprocessing.resource_tracker import unregister

            if not _warned_tracker:
                logger.info(
                    "Python <3.13: using resource_tracker.unregister() workaround "
                    "for shared memory lifecycle"
                )
                _warned_tracker = True
            # CRITICAL: Use shm._name (with leading '/') -- the tracker registered with that form
            unregister(shm._name, "shared_memory")
            logger.debug("Unregistered %s from resource tracker (Python <3.13)", shm._name)

    logger.debug("Created shared memory block %s (size=%d)", name, size)
    return shm


def _attach_shm(name: str) -> shared_memory.SharedMemory:
    """Attach to an existing SharedMemory block with the resource tracker bypassed.

    Args:
        name: Block name (without leading slash).

    Returns:
        The attached SharedMemory object.
    """
    global _warned_tracker  # noqa: PLW0603

    if _HAS_TRACK:
        shm = shared_memory.SharedMemory(name=name, create=False, track=False)
    else:
        shm = shared_memory.SharedMemory(name=name, create=False)
        if _POSIX:
            from multiprocessing.resource_tracker import unregister

            if not _warned_tracker:
                logger.info(
                    "Python <3.13: using resource_tracker.unregister() workaround "
                    "for shared memory lifecycle"
                )
                _warned_tracker = True
            unregister(shm._name, "shared_memory")

    logger.debug("Attached to shared memory block %s", name)
    return shm


def create_block(size: int) -> tuple[shared_memory.SharedMemory, str]:
    """Create a new shared memory block with an auto-generated FSHR name.

    Combines name generation with creation, retrying on name collision.

    Args:
        size: Size in bytes for the shared memory block.

    Returns:
        Tuple of (SharedMemory object, block name).

    Raises:
        AllocationError: If all retry attempts fail due to name collisions.
    """
    for _attempt in range(_MAX_RETRIES):
        name = _make_block_name()
        try:
            shm = _create_shm(name, size)
            return shm, name
        except FileExistsError:
            logger.debug("Name collision on %s, retrying (attempt %d)", name, _attempt + 1)
            continue

    msg = f"Failed to create shared memory block after {_MAX_RETRIES} retries"
    raise AllocationError(msg)


def attach_block(name: str) -> shared_memory.SharedMemory:
    """Attach to an existing shared memory block by name.

    Args:
        name: The FSHR-prefixed block name.

    Returns:
        The attached SharedMemory object.

    Raises:
        BlockNotFoundError: If no block with this name exists.
    """
    try:
        return _attach_shm(name)
    except FileNotFoundError:
        msg = f"Block '{name}' not found"
        raise BlockNotFoundError(msg) from None
