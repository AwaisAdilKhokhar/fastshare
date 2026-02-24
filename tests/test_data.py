"""Unit tests for SharedData context manager and load classmethod."""

from __future__ import annotations

import pytest

from fastshare._data import SharedData, _cache
from fastshare._errors import BlockNotFoundError, FastShareError
from fastshare._registry import attach


class TestSharedDataContextManager:
    """Tests for SharedData parent-side context manager behavior."""

    def test_context_manager_basic(self):
        """SharedData enters, exposes .name starting with FSHR_, and exits."""
        with SharedData({"key": "value"}) as sd:
            assert sd.name.startswith("FSHR_")

    def test_name_property_before_enter(self):
        """Accessing .name before __enter__ raises RuntimeError."""
        sd = SharedData({"key": "value"})
        with pytest.raises(RuntimeError, match="not entered or already exited"):
            sd.name  # noqa: B018

    def test_name_property_after_exit(self):
        """Accessing .name after __exit__ raises RuntimeError."""
        sd = SharedData({"key": "value"})
        with sd:
            pass
        with pytest.raises(RuntimeError, match="not entered or already exited"):
            sd.name  # noqa: B018

    def test_size_property(self):
        """SharedData.size returns a positive integer inside the context."""
        with SharedData({"key": "value"}) as sd:
            assert isinstance(sd.size, int)
            assert sd.size > 0

    def test_reentry_raises(self):
        """Re-entering an already-entered SharedData raises RuntimeError."""
        sd = SharedData({"key": "value"})
        with sd:
            with pytest.raises(RuntimeError, match="does not support re-entry"):
                sd.__enter__()

    def test_exit_unlinks_block(self):
        """After __exit__, the shared memory block is no longer attachable."""
        with SharedData({"key": "value"}) as sd:
            name = sd.name
        # Block should be unlinked -- attach should raise BlockNotFoundError
        with pytest.raises(BlockNotFoundError):
            attach(name)

    def test_exit_on_exception(self):
        """Block is still unlinked even when the with-body raises an exception."""
        name = None
        with pytest.raises(ValueError, match="deliberate"):
            with SharedData({"key": "value"}) as sd:
                name = sd.name
                raise ValueError("deliberate")
        assert name is not None
        with pytest.raises(BlockNotFoundError):
            attach(name)

    def test_exit_does_not_suppress_exception(self):
        """Exceptions from the with block propagate through (not suppressed)."""
        with pytest.raises(ValueError, match="test error"):
            with SharedData({"key": "value"}):
                raise ValueError("test error")

    def test_releases_object_reference(self):
        """After __enter__, SharedData._obj is None (releases original reference)."""
        with SharedData({"key": "value"}) as sd:
            assert sd._obj is None  # noqa: SLF001


class TestSharedDataLoad:
    """Tests for SharedData.load() worker-side classmethod."""

    def setup_method(self):
        """Clear cache before each test."""
        SharedData.clear_cache()

    def test_load_basic(self):
        """SharedData.load() returns equivalent object."""
        original = {"key": "value", "count": 42}
        with SharedData(original) as sd:
            loaded = SharedData.load(sd.name)
            assert loaded == original

    def test_load_cache_hit(self):
        """Second load() returns the same object (identity check)."""
        with SharedData({"key": "value"}) as sd:
            first = SharedData.load(sd.name)
            second = SharedData.load(sd.name)
            assert first is second

    def test_load_invalid_prefix(self):
        """load() with a name lacking FSHR_ prefix raises FastShareError."""
        with pytest.raises(FastShareError, match="Invalid block name"):
            SharedData.load("bad_name")

    def test_load_non_string(self):
        """load() with a non-string argument raises TypeError."""
        with pytest.raises(TypeError):
            SharedData.load(123)  # type: ignore[arg-type]

    def test_load_expired_block(self):
        """load() after the block is unlinked raises BlockNotFoundError."""
        SharedData.clear_cache()
        with SharedData({"key": "value"}) as sd:
            name = sd.name
        # Block is now unlinked
        with pytest.raises(BlockNotFoundError):
            SharedData.load(name)

    def test_clear_cache(self):
        """After clear_cache(), next load() re-deserializes (not same object)."""
        with SharedData({"key": "value"}) as sd:
            first = SharedData.load(sd.name)
            SharedData.clear_cache()
            second = SharedData.load(sd.name)
            assert first is not second
            assert first == second
