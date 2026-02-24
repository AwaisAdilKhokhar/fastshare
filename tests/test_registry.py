"""Tests for the process-local block registry and BlockHandle lifecycle."""

from __future__ import annotations

import gc

import pytest

from fastshare._errors import BlockNotFoundError
from fastshare._registry import BlockHandle, _registry, allocate, attach, unlink


class TestAllocate:
    """Tests for the allocate() function."""

    def test_creates_tracked_block(self):
        handle = allocate(1024)
        assert handle.name in _registry
        assert handle.owner is True
        assert handle.size >= 1024

    def test_block_name_starts_with_prefix(self):
        handle = allocate(512)
        assert handle.name.startswith("FSHR_")


class TestAttach:
    """Tests for the attach() function."""

    def test_creates_non_owner_handle(self):
        owner = allocate(1024)
        attached = attach(owner.name)
        assert attached.owner is False
        assert attached.name == owner.name

    def test_attach_does_not_overwrite_owner_in_registry(self):
        """Attaching should add a second handle, not replace the owner."""
        owner = allocate(1024)
        name = owner.name
        attached = attach(name)
        # Both handles should be in the registry
        handles = _registry[name]
        assert len(handles) == 2
        owners = [h for h in handles if h.owner]
        assert len(owners) == 1

    def test_attach_nonexistent_raises(self):
        with pytest.raises(BlockNotFoundError):
            attach("FSHR_nonexist")


class TestBlockHandleClose:
    """Tests for BlockHandle.close() and cleanup behavior."""

    def test_close_removes_from_registry(self):
        handle = allocate(1024)
        name = handle.name
        assert name in _registry
        handle.close()
        assert name not in _registry

    def test_owner_unlinks_on_close(self):
        """Owner close should unlink the block so it's no longer attachable."""
        handle = allocate(1024)
        name = handle.name
        handle.close()
        # Block should be gone -- attaching should fail
        with pytest.raises(BlockNotFoundError):
            attach(name)

    def test_non_owner_does_not_unlink(self):
        """Non-owner close should NOT unlink the block."""
        owner = allocate(1024)
        name = owner.name
        attached = attach(name)

        # Close the non-owner handle
        attached.close()

        # Block should still exist -- owner can still access it
        assert owner.shm.buf is not None
        # Can attach again
        attached2 = attach(name)
        attached2.close()

        # Now close owner -- block should be unlinked
        owner.close()


class TestBlockHandleFinalize:
    """Tests for weakref.finalize-based cleanup."""

    def test_finalize_cleans_on_gc(self):
        """When registry reference is removed, dropping the last reference + gc.collect()
        should trigger the finalizer and clean up the shared memory block.

        Note: The registry holds a strong reference, so we must remove it first to
        allow GC to collect the handle. In production, atexit cleanup handles
        registry-held handles. This test verifies the weakref.finalize mechanism
        works correctly when the object becomes unreachable.
        """
        handle = allocate(1024)
        name = handle.name
        assert name in _registry

        # Remove registry reference so GC can collect the handle
        _registry.pop(name)
        # Drop the local reference and force GC
        del handle
        gc.collect()

        # Finalizer should have run -- block should be unlinked
        # Verify the block is gone by trying to attach (should fail)
        with pytest.raises(BlockNotFoundError):
            attach(name)


class TestBlockHandleProperties:
    """Tests for BlockHandle property accessors."""

    def test_name_property(self):
        handle = allocate(256)
        assert isinstance(handle.name, str)
        assert handle.name.startswith("FSHR_")

    def test_owner_property(self):
        handle = allocate(256)
        assert handle.owner is True
        attached = attach(handle.name)
        assert attached.owner is False

    def test_size_property(self):
        handle = allocate(4096)
        assert handle.size >= 4096

    def test_buf_property(self):
        handle = allocate(256)
        handle.buf[0] = 123
        assert handle.buf[0] == 123

    def test_shm_property(self):
        from multiprocessing import shared_memory

        handle = allocate(256)
        assert isinstance(handle.shm, shared_memory.SharedMemory)

    def test_repr(self):
        handle = allocate(512)
        r = repr(handle)
        assert "BlockHandle(" in r
        assert handle.name in r
        assert "owner=True" in r


class TestUnlinkFunction:
    """Tests for the unlink() module function."""

    def test_unlink_registered_block(self):
        handle = allocate(1024)
        name = handle.name
        assert name in _registry
        unlink(name)
        assert name not in _registry

    def test_unlink_unknown_block_no_error(self):
        """Unlinking an unknown name should not raise."""
        unlink("FSHR_nonexist")  # should not raise
