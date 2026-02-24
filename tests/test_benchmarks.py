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


# ---------------------------------------------------------------------------
# Group: roundtrip-2gb-numpy (zero-copy path, extra large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-2gb-numpy")
def test_bench_fastshare_2gb_numpy(benchmark):
    """Benchmark fastshare for a 2 GB NumPy array (zero-copy shared memory)."""
    np = pytest.importorskip("numpy")
    data = np.ones((500_000_000,), dtype=np.float32)  # 2 GB

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.shape == (500_000_000,)


@pytest.mark.benchmark(group="roundtrip-2gb-numpy")
def test_bench_pickle_2gb_numpy(benchmark):
    """Benchmark plain pickle for a 2 GB NumPy array (comparison baseline)."""
    np = pytest.importorskip("numpy")
    data = np.ones((500_000_000,), dtype=np.float32)  # 2 GB

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.shape == (500_000_000,)


# ---------------------------------------------------------------------------
# Group: roundtrip-100mb-arrow (Arrow IPC path)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-100mb-arrow")
def test_bench_fastshare_100mb_arrow(benchmark):
    """Benchmark fastshare for a 100 MB Arrow Table (Arrow IPC shared memory)."""
    pa = pytest.importorskip("pyarrow")
    # ~100 MB: 25M int32 values
    data = pa.table({"x": pa.array(range(25_000_000), type=pa.int32())})

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.num_rows == 25_000_000


@pytest.mark.benchmark(group="roundtrip-100mb-arrow")
def test_bench_pickle_100mb_arrow(benchmark):
    """Benchmark plain pickle for a 100 MB Arrow Table (comparison baseline)."""
    pa = pytest.importorskip("pyarrow")
    data = pa.table({"x": pa.array(range(25_000_000), type=pa.int32())})

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.num_rows == 25_000_000


# ---------------------------------------------------------------------------
# Group: roundtrip-500mb-arrow (Arrow IPC path, large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-500mb-arrow")
def test_bench_fastshare_500mb_arrow(benchmark):
    """Benchmark fastshare for a 500 MB Arrow Table (Arrow IPC shared memory)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    # ~500 MB: 125M float32 values
    col = pa.array(np.ones(125_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.num_rows == 125_000_000


@pytest.mark.benchmark(group="roundtrip-500mb-arrow")
def test_bench_pickle_500mb_arrow(benchmark):
    """Benchmark plain pickle for a 500 MB Arrow Table (comparison baseline)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    col = pa.array(np.ones(125_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.num_rows == 125_000_000


# ---------------------------------------------------------------------------
# Group: roundtrip-1gb-arrow (Arrow IPC path, very large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-1gb-arrow")
def test_bench_fastshare_1gb_arrow(benchmark):
    """Benchmark fastshare for a 1 GB Arrow Table (Arrow IPC shared memory)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    # ~1 GB: 250M float32 values
    col = pa.array(np.ones(250_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.num_rows == 250_000_000


@pytest.mark.benchmark(group="roundtrip-1gb-arrow")
def test_bench_pickle_1gb_arrow(benchmark):
    """Benchmark plain pickle for a 1 GB Arrow Table (comparison baseline)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    col = pa.array(np.ones(250_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.num_rows == 250_000_000


# ---------------------------------------------------------------------------
# Group: roundtrip-2gb-arrow (Arrow IPC path, extra large)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark(group="roundtrip-2gb-arrow")
def test_bench_fastshare_2gb_arrow(benchmark):
    """Benchmark fastshare for a 2 GB Arrow Table (Arrow IPC shared memory)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    # ~2 GB: 500M float32 values
    col = pa.array(np.ones(500_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        token = write(data)
        result = read(token, readonly=False)
        return result

    result = benchmark(roundtrip)
    assert result.num_rows == 500_000_000


@pytest.mark.benchmark(group="roundtrip-2gb-arrow")
def test_bench_pickle_2gb_arrow(benchmark):
    """Benchmark plain pickle for a 2 GB Arrow Table (comparison baseline)."""
    pa = pytest.importorskip("pyarrow")
    np = pytest.importorskip("numpy")
    col = pa.array(np.ones(500_000_000, dtype=np.float32))
    data = pa.table({"x": col})

    def roundtrip():
        buf = pickle.dumps(data, protocol=5)
        return pickle.loads(buf)  # noqa: S301

    result = benchmark(roundtrip)
    assert result.num_rows == 500_000_000
