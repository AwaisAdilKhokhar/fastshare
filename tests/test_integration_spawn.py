"""Spawn-based cross-process integration tests for fastshare write/read."""

from __future__ import annotations

import pytest


# ---- Module-level child functions (must be picklable for spawn) ----


def _child_read_bytes(token: str) -> dict:
    """Child: read a bytes token and return length + prefix."""
    from fastshare import read

    obj = read(token)
    return {"length": len(obj), "prefix": obj[:5]}


def _child_read_dict(token: str, expected: dict) -> dict:
    """Child: read a dict token and compare to expected."""
    from fastshare import read

    obj = read(token)
    return {"equal": obj == expected}


def _child_read_numpy(token: str) -> dict:
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


def _child_readonly_numpy(token: str) -> dict:
    """Child: read a numpy array readonly, attempt mutation, catch error."""
    from fastshare import read

    arr = read(token, readonly=True)
    try:
        arr[0] = 999
    except ValueError:
        return {"raised": True}
    return {"raised": False}


# ---- Tests ----


@pytest.mark.integration
def test_write_read_bytes_roundtrip_spawn(spawn_child):
    """Write 2 MB bytes in parent, read in spawned child process."""
    from fastshare import write

    data = b"x" * 2_000_000
    token = write(data)

    result = spawn_child(_child_read_bytes, token)
    assert result["length"] == 2_000_000
    assert result["prefix"] == b"xxxxx"


@pytest.mark.integration
def test_write_read_dict_roundtrip_spawn(spawn_child):
    """Write a dict in parent, read and compare in spawned child process."""
    from fastshare import write

    payload = {"key": "value", "numbers": list(range(100))}
    token = write(payload)

    result = spawn_child(_child_read_dict, token, payload)
    assert result["equal"] is True


@pytest.mark.integration
def test_write_read_numpy_roundtrip_spawn(spawn_child):
    """Write a 2 MB numpy array in parent, read in spawned child process."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    arr = np.arange(250_000, dtype=np.float64)  # 250k * 8 bytes = 2 MB
    token = write(arr)

    result = spawn_child(_child_read_numpy, token)
    assert result["shape"] == (250_000,)
    assert result["dtype"] == "float64"
    assert result["sum"] == float(arr.sum())
    assert result["writeable"] is False


@pytest.mark.integration
def test_readonly_enforcement_spawn(spawn_child):
    """Write a numpy array, child reads readonly and verifies mutation raises."""
    np = pytest.importorskip("numpy")
    from fastshare import write

    arr = np.arange(100, dtype=np.float64)
    token = write(arr)

    result = spawn_child(_child_readonly_numpy, token)
    assert result["raised"] is True
