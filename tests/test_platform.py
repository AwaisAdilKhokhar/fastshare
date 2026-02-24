"""Tests for the shared memory platform abstraction layer."""

from __future__ import annotations

import warnings

import pytest

from fastshare._errors import BlockNotFoundError
from fastshare._platform import (
    _FSHR_PREFIX,
    _make_block_name,
    attach_block,
    create_block,
)


class TestMakeBlockName:
    """Tests for FSHR block name generation."""

    def test_name_starts_with_prefix(self):
        name = _make_block_name()
        assert name.startswith(_FSHR_PREFIX)

    def test_name_length_is_13(self):
        name = _make_block_name()
        assert len(name) == 13, f"Expected length 13, got {len(name)}: {name}"

    def test_name_uniqueness(self):
        """100 generated names should all be unique."""
        names = {_make_block_name() for _ in range(100)}
        assert len(names) == 100


class TestCreateBlock:
    """Tests for shared memory block creation."""

    def test_creates_valid_block(self):
        shm, name = create_block(1024)
        try:
            assert name.startswith(_FSHR_PREFIX)
            assert shm.size >= 1024
        finally:
            shm.close()
            shm.unlink()

    def test_block_buffer_is_writable(self):
        shm, name = create_block(256)
        try:
            shm.buf[0] = 42
            assert shm.buf[0] == 42
        finally:
            shm.close()
            shm.unlink()


class TestAttachBlock:
    """Tests for attaching to existing shared memory blocks."""

    def test_attach_connects_to_existing(self):
        shm, name = create_block(512)
        try:
            shm.buf[0] = 99
            shm2 = attach_block(name)
            try:
                assert shm2.buf[0] == 99
            finally:
                shm2.close()
        finally:
            shm.close()
            shm.unlink()

    def test_attach_nonexistent_raises(self):
        with pytest.raises(BlockNotFoundError):
            attach_block("FSHR_nonexist")


class TestResourceTrackerBypass:
    """Tests that the resource tracker is bypassed correctly."""

    def test_no_resource_warning_on_close(self):
        """Creating and closing a block should not produce ResourceWarning."""
        shm, name = create_block(1024)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            shm.close()
            shm.unlink()
            resource_warnings = [x for x in w if issubclass(x.category, ResourceWarning)]
            assert len(resource_warnings) == 0, (
                f"Got unexpected ResourceWarning(s): {resource_warnings}"
            )
