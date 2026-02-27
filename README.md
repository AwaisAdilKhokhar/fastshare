[![PyPI version](https://img.shields.io/pypi/v/fastshare)](https://pypi.org/project/fastshare/)
[![Python versions](https://img.shields.io/pypi/pyversions/fastshare)](https://pypi.org/project/fastshare/)
[![License](https://img.shields.io/pypi/l/fastshare)](https://github.com/AwaisAdilKhokhar/fastshare/blob/master/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/AwaisAdilKhokhar/fastshare/ci.yml?branch=master)](https://github.com/AwaisAdilKhokhar/fastshare/actions)

# fastshare

Zero-copy shared memory transfer of large Python objects between processes.

## Why fastshare?

Passing large objects between Python processes is slow. The standard approach --
`pickle.dumps()` through a `multiprocessing.Queue` or pipe -- copies the data at
least twice: once to serialize and once to push through the pipe. For a 100 MB
NumPy array, that means 200 MB+ of unnecessary copying on every transfer.

fastshare uses Python 3.8+'s pickle protocol 5 out-of-band buffers combined with
shared memory to eliminate those copies. Large buffer-backed objects (NumPy
arrays, bytearrays) are placed directly into shared memory and reconstructed on
the other side without copying. When PyArrow is installed, Arrow Tables,
RecordBatches, Arrays, and pandas DataFrames are serialized via the native Arrow
IPC format for efficient zero-copy transfer. Small objects fall back to standard
pickle automatically.

The result: drop-in `write()` and `read()` calls that work with any picklable
object -- plus PyArrow and pandas types -- transferring large data in
microseconds instead of milliseconds.

## Installation

```bash
pip install fastshare
```

With NumPy support (enables zero-copy array transfer):

```bash
pip install fastshare[numpy]
```

With PyArrow support (enables Arrow IPC transfer for Tables, DataFrames, etc.):

```bash
pip install fastshare[arrow]
```

Both:

```bash
pip install fastshare[numpy,arrow]
```

Requires Python 3.10+.

## Quick Start

Write a large object in one process, read it in another:

```python
# example_quick_start.py
import multiprocessing as mp
from fastshare import write, read


def reader(token):
    """Child process: reconstruct the object from shared memory."""
    data = read(token)
    print(f"Reader got {len(data):,} bytes, first 10: {data[:10]}")
    # Reader got 5,000,000 bytes, first 10: b'HELLOWORLD'


if __name__ == "__main__":
    # Create a 5 MB object
    payload = b"HELLOWORLD" * 500_000

    # Write to shared memory and get a token string
    token = write(payload)

    # Pass the token (a short string) to the child process
    p = mp.Process(target=reader, args=(token,))
    p.start()
    p.join()
```

The token is a lightweight string like `FSHR:shm:FSHR_a1b2c3` -- only the token
crosses the process boundary, not the data.

## SharedData Broadcast

For the common pattern of sharing one large object with a pool of workers, use
the `SharedData` context manager:

```python
# example_broadcast.py
import multiprocessing as mp
import numpy as np
from fastshare import SharedData


def worker(args):
    """Each worker loads the shared array (cached after first access)."""
    name, idx = args
    arr = SharedData.load(name)
    total = float(arr.sum())
    print(f"Worker {idx}: shape={arr.shape}, sum={total:.0f}")
    return total


if __name__ == "__main__":
    # Create a large array (100 MB)
    data = np.ones((25_000_000,), dtype=np.float32)

    with SharedData(data) as sd:
        # sd.name is the block name to pass to workers
        with mp.Pool(4) as pool:
            results = pool.map(worker, [(sd.name, i) for i in range(4)])

    # Worker 0: shape=(25000000,), sum=25000000
    # Worker 1: shape=(25000000,), sum=25000000
    # Worker 2: shape=(25000000,), sum=25000000
    # Worker 3: shape=(25000000,), sum=25000000
    print(f"All workers returned: {results}")
```

Each worker gets a zero-copy read-only view of the same shared memory block. The
data is serialized once by the parent and deserialized (with zero-copy for NumPy
arrays) once per worker process, with subsequent calls to `SharedData.load()`
returning the cached object.

## PyArrow Support

When `pyarrow` is installed, fastshare can serialize Arrow Tables, RecordBatches,
Arrays, and ChunkedArrays via the native Arrow IPC stream format -- no pickle
overhead, no extra copies.

```python
import pyarrow as pa
from fastshare import write, read

# Round-trip an Arrow Table
table = pa.table({"x": [1, 2, 3], "y": [4.0, 5.0, 6.0]})
token = write(table)
result = read(token)  # returns pa.Table
print(result.to_pydict())
# {'x': [1, 2, 3], 'y': [4.0, 5.0, 6.0]}
```

Pandas DataFrames are auto-converted to Arrow Tables when pyarrow is available.
On read they come back as Arrow Tables -- call `.to_pandas()` if you need a
DataFrame again:

```python
import pandas as pd
from fastshare import write, read

df = pd.DataFrame({"a": range(1_000_000)})
token = write(df)          # auto-converts to Arrow Table
result = read(token)       # returns pa.Table
df_back = result.to_pandas()
```

SharedData works with Arrow objects too:

```python
import pyarrow as pa
from fastshare import SharedData

table = pa.table({"col": range(10_000_000)})
with SharedData(table) as sd:
    # pass sd.name to workers; they call SharedData.load(sd.name)
    ...
```

## Benchmarks

Single-process `write()` + `read()` round-trip, measured with pytest-benchmark
on Windows 10 (Python 3.12, 8-core Intel).

| Object | Size | pickle (stdlib) | fastshare | Ratio |
|--------|------|-----------------|-----------|-------|
| `bytes` | 10 KB | 4.5 µs | 116 µs | 0.04x |
| `bytes` | 10 MB | 7.5 ms | 22.2 ms | 0.34x |
| NumPy `float32` | 100 MB | 69 ms | 45 ms | 1.5x |
| NumPy `float32` | 500 MB | 364 ms | 231 ms | 1.6x |
| NumPy `float32` | 1 GB | 863 ms | 488 ms | 1.8x |
| Arrow Table `int32` | 100 MB | 63 ms | 75 ms | 0.84x |
| Arrow Table `float32` | 500 MB | 343 ms | 471 ms | 0.73x |
| Arrow Table `float32` | 1 GB | 1,302 ms | 1,205 ms | 1.08x |
| Arrow Table `float32` | 2 GB | 2,037 ms | 1,871 ms | 1.09x |

For objects below the 1 MB threshold, fastshare delegates to standard pickle,
so the 10 KB row reflects fastshare's size-estimation overhead rather than
shared memory performance.

**Where fastshare shines:** The win grows with object size and when the object
supports pickle protocol 5 out-of-band buffers (NumPy arrays, bytearrays). At
100 MB, zero-copy deserialization avoids the full-array copy that `pickle.loads()`
must perform. Arrow Tables show overhead in single-process round-trips (Arrow IPC
serialization cost), but in multi-process scenarios the advantage compounds --
shared memory avoids the additional pipe-copy overhead that
`multiprocessing.Queue` incurs, and broadcast to N workers amortizes the single
write across all readers.

Raw benchmark output: [`benchmarks/benchmark_results.txt`](benchmarks/benchmark_results.txt)

## API Reference

### Core Functions

```python
fastshare.write(obj, *, threshold=1_000_000) -> str
```

Serialize `obj` and return a fastshare token string. Objects below `threshold`
bytes use pickle fallback; larger objects use shared memory for zero-copy
transfer. When `pyarrow` is installed, Arrow objects (Table, RecordBatch, Array,
ChunkedArray) are serialized via Arrow IPC, and pandas DataFrames are
auto-converted to Arrow Tables. If shared memory allocation fails, falls back to
pickle with a `UserWarning`.

- `obj` -- Any picklable Python object, or a PyArrow Table / RecordBatch / Array / ChunkedArray, or a pandas DataFrame (auto-converted to Arrow Table when pyarrow is installed).
- `threshold` (int) -- Size in bytes below which pickle fallback is used. Default: 1,000,000 (1 MB).
- Returns: A `"FSHR:"`-prefixed token string.
- Raises: `pickle.PicklingError` if `obj` cannot be pickled.

```python
fastshare.read(token, *, readonly=True) -> object
```

Reconstruct an object from a fastshare token. For Arrow objects, returns the
original Arrow type (Table, RecordBatch, Array, or ChunkedArray). Pandas
DataFrames come back as Arrow Tables.

- `token` (str) -- A `"FSHR:"`-prefixed token from `write()`.
- `readonly` (bool) -- If `True` (default), NumPy arrays are read-only. Set `False` to allow mutation.
- Returns: The reconstructed Python object (or Arrow type).
- Raises: `FastShareError` if the token is invalid or the shared memory block is missing.

### SharedData Class

```python
class fastshare.SharedData(obj)
```

Write-once broadcast context manager. Use for sharing large objects with
multiple worker processes. Supports any picklable object, NumPy arrays, and
PyArrow Tables / RecordBatches / Arrays / ChunkedArrays.

- Context manager: `with SharedData(obj) as sd:` serializes to shared memory. On exit the block is unlinked.
- `.name` (str) -- The FSHR-prefixed block name for passing to workers.
- `.size` (int) -- Size of the shared memory block in bytes.

```python
SharedData.load(name) -> object
```

Load a shared object by block name with per-process caching. Workers call this
with the name from the parent.

- `name` (str) -- The FSHR-prefixed block name.
- Returns: The deserialized object (NumPy arrays are read-only).
- Raises: `TypeError` if name is not a string, `BlockNotFoundError` if the block is gone.

```python
SharedData.clear_cache() -> None
```

Clear the per-process object cache. Call between batches in long-running
workers to free memory.

### Cleanup

```python
fastshare.cleanup(dry_run=False) -> CleanupResult
```

Clean up orphaned FSHR-prefixed shared memory blocks. Discovers blocks on the
system, skips blocks owned by the calling process, and unlinks the rest.
Linux only (other platforms return an empty result).

- `dry_run` (bool) -- If `True`, report without unlinking.
- Returns: `CleanupResult` with `.cleaned`, `.failed`, `.skipped` lists.

CLI equivalent:

```bash
fastshare cleanup [--dry-run] [--verbose] [--quiet]
```

### Exceptions

- `FastShareError` -- Base exception for all fastshare errors.
- `AllocationError(FastShareError)` -- Shared memory allocation failed.
- `BlockNotFoundError(FastShareError, KeyError)` -- Shared memory block not found by name.

## How It Works

fastshare uses Python's pickle protocol 5 out-of-band buffer support combined
with `multiprocessing.shared_memory`. When `write()` is called on a large
object, pickle separates the large data buffers (like NumPy array contents) from
the metadata. The buffers are written directly into a shared memory block -- no
copies. The metadata (small) is pickled normally and stored as a header.

When `read()` is called, the metadata is unpickled and the buffers are
reconstructed as zero-copy views into the shared memory block.

```
Process A                          Process B
   |                                  |
   write(obj)                         read(token)
   |                                  |
   pickle5 ──> shared memory ──> unpickle5
   (separate     (zero-copy       (reconstruct
    buffers)      transfer)        with views)
```

**Arrow IPC path:** When the object is a PyArrow type (or a pandas DataFrame
with pyarrow installed), fastshare bypasses pickle entirely and writes the data
using Arrow's native IPC stream format. A flags byte in the FSHR binary header
(`0x00` = pickle, `0x01` = Arrow IPC) tells the reader which deserialization
path to take. A one-byte type tag after the header preserves the original Arrow
type (Table, RecordBatch, Array, ChunkedArray, or pandas-converted) so `read()`
returns exactly the type that was written.

## Platform Support

|  | Python 3.10 | Python 3.11 | Python 3.12 | Python 3.13 |
|---|---|---|---|---|
| Linux | Yes | Yes | Yes | Yes |
| macOS | Yes | Yes | Yes | Yes |
| Windows | Yes | Yes | Yes | Yes |

- All platforms support shared memory transfer.
- The `cleanup` command (orphan block discovery) only works on Linux (`/dev/shm` scanning).
- The `fork` start method is not available on Windows; `spawn` works everywhere.

## License

MIT
