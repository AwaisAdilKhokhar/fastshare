"""Process-local shared memory block registry with weakref.finalize cleanup."""

from __future__ import annotations

import atexit
import logging
import os
import weakref
from multiprocessing import shared_memory

from fastshare._platform import attach_block, create_block

logger = logging.getLogger("fastshare")

# Process-local registry: {name: [BlockHandle, ...]}
# Multiple handles can exist for the same block (owner + non-owner attachments).
_registry: dict[str, list[BlockHandle]] = {}


class BlockHandle:
    """Wrapper around SharedMemory that tracks ownership and provides finalize-based cleanup.

    Owner handles (``owner=True``) will unlink the shared memory block on cleanup.
    Non-owner handles (``owner=False``) will only close the local file descriptor.

    Cleanup is guaranteed via ``weakref.finalize`` -- no ``__del__`` is used.
    """

    def __init__(self, shm: shared_memory.SharedMemory, *, owner: bool) -> None:
        self._shm = shm
        self._owner = owner
        self._name = shm.name  # user-visible name (no leading slash)

        # Register in process-local registry
        if self._name not in _registry:
            _registry[self._name] = []
        _registry[self._name].append(self)

        # weakref.finalize: guaranteed cleanup on GC or exit
        # CRITICAL: do NOT pass self or bound methods -- pass only the data needed
        self._finalizer = weakref.finalize(
            self,
            BlockHandle._cleanup,
            shm,
            self._name,
            owner,
        )

        logger.debug(
            "Registered block %s (owner=%s, pid=%d)", self._name, owner, os.getpid()
        )

    @staticmethod
    def _cleanup(shm: shared_memory.SharedMemory, name: str, owner: bool) -> None:
        """Static cleanup -- no reference to BlockHandle instance.

        This is registered as a weakref.finalize callback. It must NOT reference
        ``self`` or the ``BlockHandle`` class instance to avoid preventing GC.
        """
        try:
            shm.close()
            if owner:
                try:
                    shm.unlink()
                except OSError:
                    pass  # block may already be gone (Windows no-op, or race condition)
                logger.debug("Unlinked block %s (pid=%d)", name, os.getpid())
        except OSError:
            pass  # block may already be closed/gone

        # Remove from registry -- remove the entry list if it becomes empty
        handles = _registry.get(name)
        if handles is not None:
            # Remove handles whose finalizer has been called (alive=False)
            remaining = [h for h in handles if h._finalizer.alive]
            if remaining:
                _registry[name] = remaining
            else:
                _registry.pop(name, None)

        logger.debug("Cleaned up block %s (owner=%s, pid=%d)", name, owner, os.getpid())

    def close(self) -> None:
        """Explicitly clean up this handle.

        Calls the weakref.finalize callback which closes (and unlinks if owner)
        the shared memory block and removes it from the registry.
        """
        self._finalizer()

    @property
    def name(self) -> str:
        """The FSHR-prefixed block name."""
        return self._name

    @property
    def owner(self) -> bool:
        """Whether this handle owns (and will unlink) the block."""
        return self._owner

    @property
    def shm(self) -> shared_memory.SharedMemory:
        """The underlying SharedMemory object."""
        return self._shm

    @property
    def buf(self) -> memoryview:
        """The shared memory buffer as a memoryview."""
        return self._shm.buf

    @property
    def size(self) -> int:
        """The size of the shared memory block in bytes."""
        return self._shm.size

    def __repr__(self) -> str:
        return f"BlockHandle(name={self._name}, owner={self._owner}, size={self._shm.size})"


def allocate(size: int) -> BlockHandle:
    """Allocate a new shared memory block and return an owner BlockHandle.

    Args:
        size: Size in bytes for the shared memory block.

    Returns:
        A BlockHandle with ``owner=True``, tracked in the registry.
    """
    shm, _name = create_block(size)
    return BlockHandle(shm, owner=True)


def attach(name: str) -> BlockHandle:
    """Attach to an existing shared memory block by name.

    Args:
        name: The FSHR-prefixed block name.

    Returns:
        A BlockHandle with ``owner=False``, tracked in the registry.

    Raises:
        BlockNotFoundError: If no block with this name exists.
    """
    shm = attach_block(name)
    return BlockHandle(shm, owner=False)


def unlink(name: str) -> None:
    """Unlink a shared memory block by name.

    If the block is tracked in the registry, all handles for that block are closed.
    Otherwise, attempts to attach and unlink directly.

    Args:
        name: The FSHR-prefixed block name.
    """
    if name in _registry:
        # Close all handles for this block (copy list to avoid mutation during iteration)
        for handle in list(_registry.get(name, [])):
            handle.close()
    else:
        # Block not in our registry -- try to attach and unlink directly
        try:
            shm = attach_block(name)
            shm.close()
            shm.unlink()
        except Exception:  # noqa: BLE001
            pass


def _atexit_cleanup() -> None:
    """Belt-and-suspenders cleanup: unlink all owned blocks at interpreter exit.

    This runs in addition to weakref.finalize callbacks. It iterates a copy of
    the registry keys to avoid mutation-during-iteration issues.
    """
    count = 0
    for name in list(_registry):
        handles = _registry.get(name, [])
        for handle in list(handles):
            handle.close()
            count += 1
    logger.debug("atexit cleanup: processed %d handles", count)


# Register the atexit handler at module import time
atexit.register(_atexit_cleanup)
