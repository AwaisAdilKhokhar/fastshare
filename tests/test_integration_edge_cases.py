"""Edge case integration tests for fastshare.

Tests large NumPy arrays, non-contiguous arrays, below-threshold pickle
fallback, allocation failure fallback, and readonly enforcement across
process boundaries.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---- Module-level child functions (must be picklable for spawn) ----


def _child_large_numpy(token: str) -> dict:
    """Child: read a large numpy array token and return metadata."""
    from fastshare import read

    arr = read(token)
    return {
        "shape": tuple(arr.shape),
        "dtype": str(arr.dtype),
        "sum": float(arr.sum()),
        "nbytes": int(arr.nbytes),
    }


def _child_non_contiguous_numpy(token: str) -> dict:
    """Child: read a non-contiguous numpy array and return values."""
    from fastshare import read

    arr = read(token)
    return {
        "shape": tuple(arr.shape),
        "values": arr.tolist(),
        "is_c_contiguous": bool(arr.flags["C_CONTIGUOUS"]),
    }


def _child_read_small_object(token: str) -> dict:
    """Child: read a small pickle-fallback token and return value."""
    from fastshare import read

    obj = read(token)
    return {"value": obj}


def _child_readonly_numpy(token: str) -> dict:
    """Child: read numpy array readonly, attempt mutation, catch error."""
    from fastshare import read

    arr = read(token, readonly=True)
    try:
        arr[0] = 999
    except (ValueError, TypeError) as exc:
        return {"raised": True, "error_type": type(exc).__name__}
    return {"raised": False, "error_type": None}


# ---- Tests ----


@pytest.mark.integration
def test_large_numpy_array_cross_process(spawn_child):
    """A 2 MB numpy array transfers correctly across processes via shared memory."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    arr = np.ones((500_000,), dtype=np.float32)  # 500k * 4 bytes = 2 MB
    token = write(arr)

    result = spawn_child(_child_large_numpy, token)
    assert result["shape"] == (500_000,)
    assert result["dtype"] == "float32"
    assert result["sum"] == pytest.approx(500_000.0)
    assert result["nbytes"] == 2_000_000


@pytest.mark.integration
def test_non_contiguous_numpy_array(spawn_child):
    """Non-contiguous NumPy arrays are handled without corruption."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    # Create a non-contiguous array: every other row of a 10x10 matrix
    base = np.arange(100).reshape(10, 10)
    non_contig = base[::2]  # Shape (5, 10), non-contiguous
    assert not non_contig.flags["C_CONTIGUOUS"], "Array should be non-contiguous"

    expected_values = non_contig.tolist()
    token = write(non_contig)

    result = spawn_child(_child_non_contiguous_numpy, token)
    assert result["shape"] == (5, 10)
    assert result["values"] == expected_values


@pytest.mark.integration
def test_below_threshold_pickle_fallback(spawn_child):
    """Below-threshold objects fall back to pickle automatically."""
    from fastshare import write

    small_obj = {"small": True}
    token = write(small_obj)

    # Verify pickle path token prefix
    assert token.startswith("FSHR:pkl:"), f"Expected pickle fallback, got token: {token[:20]}"

    result = spawn_child(_child_read_small_object, token)
    assert result["value"] == {"small": True}


@pytest.mark.integration
def test_allocation_failure_fallback():
    """Allocation failure falls back to pickle with a UserWarning."""
    from fastshare import write

    # Patch _create_shm to always raise OSError, simulating allocation failure
    with patch("fastshare._platform._create_shm", side_effect=OSError("mock alloc fail")):
        with pytest.warns(UserWarning, match="Shared memory allocation failed"):
            # Use a large-ish object above default threshold (1 MB)
            big_data = b"x" * 2_000_000
            token = write(big_data)

    assert token.startswith("FSHR:pkl:"), f"Expected pickle fallback, got: {token[:20]}"


@pytest.mark.integration
def test_readonly_enforcement_cross_process(spawn_child):
    """Readonly enforcement prevents writes to read() results in child processes."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    arr = np.arange(100, dtype=np.float64)
    token = write(arr)

    result = spawn_child(_child_readonly_numpy, token)
    assert result["raised"] is True, "Expected readonly enforcement to raise"
    assert result["error_type"] in ("ValueError", "TypeError"), (
        f"Unexpected error type: {result['error_type']}"
    )
