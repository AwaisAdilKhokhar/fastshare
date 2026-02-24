"""Performance benchmarks comparing fastshare vs plain pickle.

Run with: pytest tests/test_benchmarks.py -v --benchmark-enable
These are disabled by default in normal test runs (--benchmark-disable).
"""

from __future__ import annotations

import pickle

import pytest

from fastshare import read, write


# ---------------------------------------------------------------------------
# Group: roundtrip-10kb (below threshold -- both use pickle)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-10kb")
def test_bench_fastshare_10kb(benchmark):
    """Benchmark fastshare for a 10 KB object (below threshold, uses pickle path)."""
    data = b"x" * 10_000

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert len(result) == 10_000


@pytest.mark.benchmark(group="roundtrip-10kb")
def test_bench_pickle_10kb(benchmark):
    """Benchmark plain pickle for a 10 KB object (comparison baseline)."""
    data = b"x" * 10_000

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert len(result) == 10_000


# ---------------------------------------------------------------------------
# Group: roundtrip-10mb (above threshold -- fastshare uses shared memory)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-10mb")
def test_bench_fastshare_10mb(benchmark):
    """Benchmark fastshare for a 10 MB object (above threshold, uses shared memory)."""
    data = b"x" * 10_000_000

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert len(result) == 10_000_000


@pytest.mark.benchmark(group="roundtrip-10mb")
def test_bench_pickle_10mb(benchmark):
    """Benchmark plain pickle for a 10 MB object (comparison baseline)."""
    data = b"x" * 10_000_000

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert len(result) == 10_000_000


# ---------------------------------------------------------------------------
# Group: roundtrip-100mb-numpy (zero-copy path)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-100mb-numpy")
def test_bench_fastshare_100mb_numpy(benchmark):
    """Benchmark fastshare for a 100 MB NumPy array (zero-copy shared memory)."""
    np = pytest.importorskip("numpy")
    data = np.ones((25_000_000,), dtype=np.float32)  # 100 MB

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.shape == (25_000_000,)


@pytest.mark.benchmark(group="roundtrip-100mb-numpy")
def test_bench_pickle_100mb_numpy(benchmark):
    """Benchmark plain pickle for a 100 MB NumPy array (comparison baseline)."""
    np = pytest.importorskip("numpy")
    data = np.ones((25_000_000,), dtype=np.float32)  # 100 MB

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.shape == (25_000_000,)


# ---------------------------------------------------------------------------
# Group: roundtrip-500mb-numpy (zero-copy path, large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-500mb-numpy")
def test_bench_fastshare_500mb_numpy(benchmark):
    """Benchmark fastshare for a 500 MB NumPy array (zero-copy shared memory)."""
    np = pytest.importorskip("numpy")
    data = np.ones((125_000_000,), dtype=np.float32)  # 500 MB

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.shape == (125_000_000,)


@pytest.mark.benchmark(group="roundtrip-500mb-numpy")
def test_bench_pickle_500mb_numpy(benchmark):
    """Benchmark plain pickle for a 500 MB NumPy array (comparison baseline)."""
    np = pytest.importorskip("numpy")
    data = np.ones((125_000_000,), dtype=np.float32)  # 500 MB

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.shape == (125_000_000,)


# ---------------------------------------------------------------------------
# Group: roundtrip-1gb-numpy (zero-copy path, very large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-1gb-numpy")
def test_bench_fastshare_1gb_numpy(benchmark):
    """Benchmark fastshare for a 1 GB NumPy array (zero-copy shared memory)."""
    np = pytest.importorskip("numpy")
    data = np.ones((250_000_000,), dtype=np.float32)  # 1 GB

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.shape == (250_000_000,)


@pytest.mark.benchmark(group="roundtrip-1gb-numpy")
def test_bench_pickle_1gb_numpy(benchmark):
    """Benchmark plain pickle for a 1 GB NumPy array (comparison baseline)."""
    np = pytest.importorskip("numpy")
    data = np.ones((250_000_000,), dtype=np.float32)  # 1 GB

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.shape == (250_000_000,)
