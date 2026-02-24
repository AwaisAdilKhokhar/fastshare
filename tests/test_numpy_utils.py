"""Tests for fastshare._numpy_utils: contiguity check, readonly enforcement, numpy detection."""

from __future__ import annotations

import warnings

import pytest

from fastshare._numpy_utils import check_contiguity, enforce_readonly, has_numpy

np = pytest.importorskip("numpy")


# ---------------------------------------------------------------------------
# has_numpy()
# ---------------------------------------------------------------------------


class TestHasNumpy:
    def test_returns_true_when_installed(self) -> None:
        assert has_numpy() is True


# ---------------------------------------------------------------------------
# check_contiguity()
# ---------------------------------------------------------------------------


class TestCheckContiguity:
    def test_c_contiguous_unchanged(self) -> None:
        arr = np.arange(10, dtype=np.float64)
        result = check_contiguity(arr)
        assert result is arr  # same object, no copy

    def test_c_contiguous_no_warning(self) -> None:
        arr = np.arange(10, dtype=np.float64)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            check_contiguity(arr)  # should NOT warn

    def test_noncontiguous_slice_warns_and_copies(self) -> None:
        arr = np.arange(20, dtype=np.float64)
        sliced = arr[::2]  # non-contiguous
        assert not sliced.flags.c_contiguous

        with pytest.warns(UserWarning, match="Non-contiguous array detected"):
            result = check_contiguity(sliced)

        assert result.flags.c_contiguous
        np.testing.assert_array_equal(result, sliced)

    def test_noncontiguous_transpose_warns_and_copies(self) -> None:
        arr = np.arange(12, dtype=np.float64).reshape(3, 4)
        transposed = arr.T
        assert not transposed.flags.c_contiguous

        with pytest.warns(UserWarning, match="Non-contiguous array detected"):
            result = check_contiguity(transposed)

        assert result.flags.c_contiguous
        np.testing.assert_array_equal(result, transposed)

    def test_warning_includes_shape_and_strides(self) -> None:
        arr = np.arange(20, dtype=np.float64)
        sliced = arr[::2]

        with pytest.warns(UserWarning, match=r"shape=.*strides="):
            check_contiguity(sliced)

    def test_non_ndarray_returned_unchanged(self) -> None:
        obj = {"key": "value"}
        assert check_contiguity(obj) is obj

    def test_plain_int_returned_unchanged(self) -> None:
        assert check_contiguity(42) == 42


# ---------------------------------------------------------------------------
# enforce_readonly()
# ---------------------------------------------------------------------------


class TestEnforceReadonly:
    def test_single_ndarray(self) -> None:
        arr = np.arange(10, dtype=np.float64)
        assert arr.flags.writeable is True
        result = enforce_readonly(arr)
        assert result is arr
        assert arr.flags.writeable is False

    def test_dict_containing_arrays(self) -> None:
        a = np.zeros(5)
        b = np.ones(3)
        d = {"a": a, "b": b}
        enforce_readonly(d)
        assert a.flags.writeable is False
        assert b.flags.writeable is False

    def test_list_of_arrays(self) -> None:
        arrays = [np.zeros(5), np.ones(3)]
        enforce_readonly(arrays)
        for arr in arrays:
            assert arr.flags.writeable is False

    def test_nested_dict_of_lists_of_arrays(self) -> None:
        inner_arr = np.arange(4)
        nested = {"level1": [inner_arr, np.zeros(2)]}
        enforce_readonly(nested)
        assert inner_arr.flags.writeable is False
        assert nested["level1"][1].flags.writeable is False

    def test_non_ndarray_returned_unchanged(self) -> None:
        obj = "hello"
        assert enforce_readonly(obj) is obj

    def test_writing_to_readonly_raises(self) -> None:
        arr = np.arange(10, dtype=np.float64)
        enforce_readonly(arr)
        with pytest.raises(ValueError, match="read-only"):
            arr[0] = 999.0

    def test_tuple_containing_arrays(self) -> None:
        a = np.zeros(5)
        t = (a,)
        enforce_readonly(t)
        assert a.flags.writeable is False
