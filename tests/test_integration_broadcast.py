"""SharedData broadcast and caching integration tests.

Tests that SharedData delivers identical data to multiple worker processes,
that per-process caching returns the same object on repeated load() calls,
and that NumPy arrays broadcast correctly via SharedData.
"""

from __future__ import annotations

import pytest


# ---- Module-level child functions (must be picklable for spawn) ----


def _broadcast_worker(name: str, expected: dict) -> dict:
    """Child: load SharedData by name and compare to expected."""
    from fastshare import SharedData

    obj = SharedData.load(name)
    return {"equal": obj == expected, "type": type(obj).__name__}


def _caching_worker(name: str) -> dict:
    """Child: load SharedData twice and check identity (caching)."""
    from fastshare import SharedData

    obj1 = SharedData.load(name)
    obj2 = SharedData.load(name)
    return {"is_same": obj1 is obj2, "equal": obj1 == {"cached": True}}


def _broadcast_numpy_worker(name: str) -> dict:
    """Child: load SharedData numpy array and return metadata."""
    import numpy as np  # noqa: F401
    from fastshare import SharedData

    arr = SharedData.load(name)
    return {
        "shape": tuple(arr.shape),
        "dtype": str(arr.dtype),
        "sum": float(arr.sum()),
    }


# ---- Tests ----


@pytest.mark.integration
def test_shared_data_broadcast_multi_worker(spawn_child):
    """SharedData broadcasts identical data to 3 concurrent workers."""
    from fastshare import SharedData

    payload = {"data": list(range(1000))}

    with SharedData(payload) as sd:
        results = [
            spawn_child(_broadcast_worker, sd.name, payload)
            for _ in range(3)
        ]

    for i, result in enumerate(results):
        assert result["equal"] is True, f"Worker {i} got non-equal data"
        assert result["type"] == "dict", f"Worker {i} got type {result['type']}"


@pytest.mark.integration
def test_shared_data_per_process_caching(spawn_child):
    """SharedData.load() returns cached (identical) object on repeated calls."""
    from fastshare import SharedData

    with SharedData({"cached": True}) as sd:
        result = spawn_child(_caching_worker, sd.name)

    assert result["is_same"] is True, "load() did not return cached object"
    assert result["equal"] is True, "Cached object has wrong value"


@pytest.mark.integration
def test_shared_data_broadcast_numpy(spawn_child):
    """SharedData broadcasts a large NumPy array to 2 workers correctly."""
    np = pytest.importorskip("numpy")
    from fastshare import SharedData

    arr = np.arange(100_000, dtype=np.float64)  # 800 KB, above threshold
    expected_sum = float(arr.sum())

    with SharedData(arr) as sd:
        results = [
            spawn_child(_broadcast_numpy_worker, sd.name)
            for _ in range(2)
        ]

    for i, result in enumerate(results):
        assert result["shape"] == (100_000,), f"Worker {i} got shape {result['shape']}"
        assert result["dtype"] == "float64", f"Worker {i} got dtype {result['dtype']}"
        assert result["sum"] == expected_sum, f"Worker {i} got sum {result['sum']}"
