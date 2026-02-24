"""Comprehensive tests for the public write/read API."""

from __future__ import annotations

from unittest.mock import patch

import pytest

import fastshare
from fastshare._api import read, write
from fastshare._errors import FastShareError


# ---------------------------------------------------------------------------
# Token format tests
# ---------------------------------------------------------------------------


class TestTokenFormat:
    """Verify tokens have the expected FSHR: prefix and mode segment."""

    def test_small_dict_uses_pickle_token(self):
        token = write({"key": "val"})
        assert token.startswith("FSHR:pkl:")

    def test_large_bytes_uses_shm_token(self):
        token = write(b"x" * 2_000_000)
        assert token.startswith("FSHR:shm:")

    def test_custom_low_threshold_forces_shm(self):
        token = write(b"x" * 100, threshold=50)
        assert token.startswith("FSHR:shm:")

    def test_custom_high_threshold_forces_pickle(self):
        token = write(b"x" * 100, threshold=200)
        assert token.startswith("FSHR:pkl:")


# ---------------------------------------------------------------------------
# Round-trip tests (CORE-01, CORE-02)
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Verify write -> read round-trips for various Python object types."""

    def test_small_dict(self):
        obj = {"a": 1, "b": [2, 3]}
        assert read(write(obj)) == obj

    def test_small_list(self):
        obj = [1, "two", 3.0, None, True]
        assert read(write(obj)) == obj

    def test_small_bytes(self):
        obj = b"hello world"
        assert read(write(obj)) == obj

    def test_large_bytes_via_shm(self):
        obj = b"x" * 2_000_000
        token = write(obj)
        assert token.startswith("FSHR:shm:")
        assert read(token) == obj

    def test_nested_structure_with_large_bytes(self):
        obj = {"data": b"x" * 2_000_000, "meta": {"key": "val"}}
        result = read(write(obj))
        assert result["meta"] == {"key": "val"}
        assert result["data"] == b"x" * 2_000_000


# ---------------------------------------------------------------------------
# NumPy round-trip tests
# ---------------------------------------------------------------------------


class TestNumpyRoundTrip:
    """Verify NumPy arrays round-trip correctly through write/read."""

    @pytest.fixture(autouse=True)
    def _skip_without_numpy(self):
        pytest.importorskip("numpy")

    def test_large_float64_array(self):
        import numpy as np

        arr = np.zeros(500_000, dtype=np.float64)  # 4 MB
        token = write(arr)
        assert token.startswith("FSHR:shm:")
        result = read(token, readonly=False)
        assert np.array_equal(arr, result)

    def test_array_preserves_dtype(self):
        import numpy as np

        arr = np.arange(100, dtype=np.int32)
        result = read(write(arr), readonly=False)
        assert result.dtype == np.int32
        assert np.array_equal(arr, result)

    def test_2d_array_preserves_shape(self):
        import numpy as np

        arr = np.zeros((100, 100))
        result = read(write(arr), readonly=False)
        assert result.shape == (100, 100)
        assert np.array_equal(arr, result)


# ---------------------------------------------------------------------------
# Threshold fallback tests (CORE-03)
# ---------------------------------------------------------------------------


class TestThresholdFallback:
    """Verify size-based routing between pickle and shared memory."""

    def test_tiny_int_uses_pickle(self):
        token = write(42)
        assert token.startswith("FSHR:pkl:")

    def test_threshold_zero_forces_shm(self):
        token = write(42, threshold=0)
        assert token.startswith("FSHR:shm:")


# ---------------------------------------------------------------------------
# Allocation failure fallback test (CORE-04)
# ---------------------------------------------------------------------------


class TestAllocationFallback:
    """Verify fallback to pickle when shared memory allocation fails."""

    def test_oserror_falls_back_to_pickle_with_warning(self):
        with patch(
            "fastshare._api.serialize_to_block",
            side_effect=OSError("mock shm failure"),
        ):
            with pytest.warns(UserWarning, match="allocation failed"):
                token = write(b"x" * 2_000_000)
        assert token.startswith("FSHR:pkl:")
        # Token still works
        assert read(token) == b"x" * 2_000_000


# ---------------------------------------------------------------------------
# Readonly tests (SAFE-03)
# ---------------------------------------------------------------------------


class TestReadonly:
    """Verify readonly enforcement on read()."""

    @pytest.fixture(autouse=True)
    def _skip_without_numpy(self):
        pytest.importorskip("numpy")

    def test_readonly_true_makes_array_non_writeable(self):
        import numpy as np

        arr = np.zeros(500_000, dtype=np.float64)
        token = write(arr)
        result = read(token, readonly=True)
        assert result.flags.writeable is False

    def test_readonly_false_keeps_array_writeable(self):
        import numpy as np

        arr = np.zeros(500_000, dtype=np.float64)
        token = write(arr)
        result = read(token, readonly=False)
        assert result.flags.writeable is True

    def test_readonly_nested_dict_with_array(self):
        import numpy as np

        obj = {"arr": np.zeros(10)}
        token = write(obj)
        result = read(token, readonly=True)
        assert result["arr"].flags.writeable is False

    def test_write_to_readonly_raises_valueerror(self):
        import numpy as np

        arr = np.zeros(500_000, dtype=np.float64)
        token = write(arr)
        result = read(token, readonly=True)
        with pytest.raises(ValueError, match="read-only"):
            result[0] = 999.0


# ---------------------------------------------------------------------------
# Non-contiguous array test (NUMP-02)
# ---------------------------------------------------------------------------


class TestNonContiguous:
    """Verify non-contiguous arrays are warned and copied before write."""

    @pytest.fixture(autouse=True)
    def _skip_without_numpy(self):
        pytest.importorskip("numpy")

    def test_non_contiguous_slice_warns_and_roundtrips(self):
        import numpy as np

        arr = np.arange(100, dtype=np.float64)
        sliced = arr[::2]  # non-contiguous
        assert not sliced.flags.c_contiguous

        with pytest.warns(UserWarning, match="Non-contiguous"):
            token = write(sliced)

        result = read(token, readonly=False)
        assert np.array_equal(result, arr[::2])


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify that invalid tokens raise FastShareError."""

    def test_invalid_token_no_prefix(self):
        with pytest.raises(FastShareError, match="Invalid fastshare token"):
            read("invalid_token")

    def test_shm_nonexistent_block(self):
        with pytest.raises(FastShareError, match="Shared memory block not found"):
            read("FSHR:shm:FSHR_nonexistent")

    def test_unknown_mode(self):
        with pytest.raises(FastShareError, match="Unknown token mode"):
            read("FSHR:xyz:data")


# ---------------------------------------------------------------------------
# Public API import test
# ---------------------------------------------------------------------------


class TestPublicAPI:
    """Verify write and read are importable from the top-level package."""

    def test_write_importable_from_fastshare(self):
        assert hasattr(fastshare, "write")
        assert callable(fastshare.write)

    def test_read_importable_from_fastshare(self):
        assert hasattr(fastshare, "read")
        assert callable(fastshare.read)

    def test_direct_import(self):
        from fastshare import read as r
        from fastshare import write as w

        assert callable(w)
        assert callable(r)

    def test_write_module(self):
        assert fastshare.write.__module__ == "fastshare._api"

    def test_read_module(self):
        assert fastshare.read.__module__ == "fastshare._api"


# ---------------------------------------------------------------------------
# SharedData public API import tests (DATA-01, DATA-02)
# ---------------------------------------------------------------------------


class TestSharedDataPublicAPI:
    """Verify SharedData is importable and usable from the top-level package."""

    def setup_method(self):
        """Clear SharedData cache before each test."""
        from fastshare import SharedData

        SharedData.clear_cache()

    def test_shared_data_importable(self):
        """SharedData is importable from fastshare and listed in __all__."""
        from fastshare import SharedData

        assert SharedData is not None
        assert "SharedData" in fastshare.__all__

    def test_shared_data_round_trip_via_public_import(self):
        """Full round-trip: create SharedData, load by name, verify data matches."""
        from fastshare import SharedData

        original = {"hello": "world"}
        with SharedData(original) as sd:
            name = sd.name
            loaded = SharedData.load(name)
            assert loaded == original

    def test_shared_data_load_via_public_import(self):
        """SharedData.load and SharedData.clear_cache are accessible from public import."""
        from fastshare import SharedData

        assert hasattr(SharedData, "load")
        assert callable(SharedData.load)
        assert hasattr(SharedData, "clear_cache")
        assert callable(SharedData.clear_cache)
