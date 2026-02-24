"""Fork-based cross-process integration tests for fastshare write/read.

These tests are skipped on Windows where fork is not available.
"""

from __future__ import annotations

import sys

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.fork_only,
    pytest.mark.skipif(sys.platform == "win32", reason="fork not available on Windows"),
]


# ---- Module-level child functions (consistent with spawn pattern) ----


def _child_read_bytes_fork(token: str) -> dict:
    """Child: read a bytes token and return length + prefix."""
    from fastshare import read

    obj = read(token)
    return {"length": len(obj), "prefix": obj[:5]}


def _child_read_numpy_fork(token: str) -> dict:
    """Child: read a numpy array token and return metadata."""
    import numpy as np  # noqa: F401
    from fastshare import read

    arr = read(token)
    return {
        "shape": arr.shape,
        "dtype": str(arr.dtype),
        "sum": float(arr.sum()),
        "writeable": bool(arr.flags.writeable),
    }


# ---- Tests ----


def test_write_read_bytes_roundtrip_fork(fork_child):
    """Write 2 MB bytes in parent, read in forked child process."""
    from fastshare import write

    data = b"x" * 2_000_000
    token = write(data)

    result = fork_child(_child_read_bytes_fork, token)
    assert result["length"] == 2_000_000
    assert result["prefix"] == b"xxxxx"


def test_write_read_numpy_roundtrip_fork(fork_child):
    """Write a 2 MB numpy array in parent, read in forked child process."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    arr = np.arange(250_000, dtype=np.float64)  # 250k * 8 bytes = 2 MB
    token = write(arr)

    result = fork_child(_child_read_numpy_fork, token)
    assert result["shape"] == (250_000,)
    assert result["dtype"] == "float64"
    assert result["sum"] == float(arr.sum())
    assert result["writeable"] is False
