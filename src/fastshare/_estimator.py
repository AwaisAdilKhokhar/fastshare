"""Fast heuristic size estimation for threshold comparison.

Provides a quick estimate of an object's memory footprint in bytes,
used to decide whether to route through shared memory or standard pickle.
Exact for NumPy arrays (``ndarray.nbytes``), PyArrow objects (``nbytes``),
and bytes-like objects (``len``).
Uses bounded sampling (max 8 items) for collections to avoid traversing
massive structures.
"""

from __future__ import annotations

import sys

# Maximum number of collection items to sample for heuristic estimation.
_MAX_SAMPLE: int = 8


def estimate_size(obj: object) -> int:
    """Return an estimated size in bytes for *obj*.

    The estimate is used for threshold comparison (shared memory vs pickle
    fallback) and does **not** need to be exact for arbitrary objects.

    Strategy:
      1. **NumPy ndarray** -- exact via ``ndarray.nbytes``
      2. **PyArrow Table/RecordBatch/Array/ChunkedArray** -- exact via ``nbytes``
      3. **bytes / bytearray / memoryview** -- exact via ``len()``
      3. **dict** -- container overhead + sampled average value size * count
      4. **list / tuple** -- container overhead + sampled average item size * count
      5. **Everything else** -- ``sys.getsizeof(obj)`` (shallow)

    NumPy is imported lazily so that non-numpy users never pay the import
    cost.  If numpy is not installed the ndarray fast-path is silently
    skipped.
    """
    # --- NumPy fast path (exact) ----------------------------------------
    try:
        import numpy as np  # noqa: PLC0415

        if isinstance(obj, np.ndarray):
            return int(obj.nbytes)
    except ImportError:
        pass

    # --- Arrow fast path (exact via nbytes) --------------------------------
    try:
        import pyarrow as pa  # noqa: PLC0415

        if isinstance(obj, (pa.Table, pa.RecordBatch, pa.Array, pa.ChunkedArray)):
            return int(obj.nbytes)
    except ImportError:
        pass

    # --- bytes-like fast path (exact) -----------------------------------
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return len(obj)

    # --- dict (bounded sampling) ----------------------------------------
    if isinstance(obj, dict):
        container = sys.getsizeof(obj)
        if not obj:
            return container
        values = list(obj.values())
        sample = values[: _MAX_SAMPLE]
        avg = sum(sys.getsizeof(v) for v in sample) / len(sample)
        return container + int(avg * len(obj))

    # --- list / tuple (bounded sampling) --------------------------------
    if isinstance(obj, (list, tuple)):
        container = sys.getsizeof(obj)
        if not obj:
            return container
        sample = obj[: _MAX_SAMPLE]
        avg = sum(sys.getsizeof(v) for v in sample) / len(sample)
        return container + int(avg * len(obj))

    # --- scalar / other (shallow) ---------------------------------------
    return sys.getsizeof(obj)
