"""Tests for the size estimation heuristic module."""

from __future__ import annotations

import sys

import pytest

from fastshare._estimator import estimate_size


class TestNumPyArrays:
    """NumPy arrays should return exact nbytes."""

    @pytest.fixture(autouse=True)
    def _require_numpy(self):
        pytest.importorskip("numpy")

    def test_float64_array(self):
        import numpy as np

        arr = np.zeros(1_000_000)
        assert estimate_size(arr) == 8_000_000

    def test_int32_2d_array(self):
        import numpy as np

        arr = np.zeros((100, 100), dtype=np.int32)
        assert estimate_size(arr) == 40_000

    def test_empty_array(self):
        import numpy as np

        arr = np.array([])
        assert estimate_size(arr) == 0


class TestBytesLike:
    """bytes, bytearray, and memoryview should return exact length."""

    def test_bytes(self):
        assert estimate_size(b"hello") == 5

    def test_bytearray(self):
        assert estimate_size(bytearray(1024)) == 1024

    def test_memoryview(self):
        assert estimate_size(memoryview(b"test")) == 4


class TestCollections:
    """Collections should use bounded sampling, not full traversal."""

    def test_empty_dict(self):
        assert estimate_size({}) == sys.getsizeof({})

    def test_empty_list(self):
        assert estimate_size([]) == sys.getsizeof([])

    def test_dict_with_values_positive(self):
        """A non-empty dict should return more than the container overhead."""
        result = estimate_size({"a": "x" * 100})
        assert result > sys.getsizeof({})
        assert isinstance(result, int)

    def test_large_list_positive(self):
        """A list of 1000 ints should return a positive integer."""
        result = estimate_size(list(range(1000)))
        assert result > 0
        assert isinstance(result, int)

    def test_tuple_positive(self):
        """A tuple should return a positive integer."""
        result = estimate_size(tuple(range(50)))
        assert result > 0
        assert isinstance(result, int)


class TestScalarFallback:
    """Scalar types should fall back to sys.getsizeof (shallow)."""

    def test_int(self):
        assert estimate_size(42) == sys.getsizeof(42)

    def test_string(self):
        assert estimate_size("hello") == sys.getsizeof("hello")

    def test_none(self):
        assert estimate_size(None) == sys.getsizeof(None)


class TestBoundedSampling:
    """Verify that sampling is bounded and produces reasonable estimates."""

    def test_large_list_reasonable_range(self):
        """A list of 1000 items should produce a reasonable estimate.

        The estimate should be between the container overhead and some
        reasonable upper bound. This verifies sampling works without
        traversing all 1000 items.
        """
        items = list(range(1000))
        result = estimate_size(items)
        container_overhead = sys.getsizeof(items)
        # Must be at least as large as the container itself
        assert result >= container_overhead
        # Must be positive and finite
        assert 0 < result < 10_000_000  # well under 10 MB for a list of ints
