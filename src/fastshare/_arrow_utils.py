"""PyArrow utility functions: availability detection, type checking, conversion helpers."""

from __future__ import annotations

# Lazy pyarrow availability cache
_arrow_available: bool | None = None


def has_arrow() -> bool:
    """Return True if pyarrow is importable, caching the result after first call."""
    global _arrow_available  # noqa: PLW0603
    if _arrow_available is None:
        try:
            import pyarrow  # noqa: F401

            _arrow_available = True
        except ImportError:
            _arrow_available = False
    return _arrow_available


def is_arrow_type(obj: object) -> bool:
    """Return True if obj is a supported PyArrow type (Table, RecordBatch, Array, ChunkedArray)."""
    if not has_arrow():
        return False
    import pyarrow as pa

    return isinstance(obj, (pa.Table, pa.RecordBatch, pa.Array, pa.ChunkedArray))


# Arrow type tag constants for round-trip type preservation
ARROW_TYPE_TABLE = 0x01
ARROW_TYPE_RECORD_BATCH = 0x02
ARROW_TYPE_ARRAY = 0x03
ARROW_TYPE_CHUNKED_ARRAY = 0x04
ARROW_TYPE_PANDAS_DATAFRAME = 0x05  # auto-converted from pandas, read back as Arrow Table


def get_arrow_type_tag(obj: object) -> int:
    """Return the type tag byte for a supported Arrow object."""
    import pyarrow as pa

    if isinstance(obj, pa.Table):
        return ARROW_TYPE_TABLE
    if isinstance(obj, pa.RecordBatch):
        return ARROW_TYPE_RECORD_BATCH
    if isinstance(obj, pa.ChunkedArray):
        return ARROW_TYPE_CHUNKED_ARRAY
    if isinstance(obj, pa.Array):
        return ARROW_TYPE_ARRAY
    msg = f"Unsupported Arrow type: {type(obj).__name__}"
    raise TypeError(msg)


def restore_arrow_type(table: object, type_tag: int) -> object:
    """Convert an IPC-deserialized Table back to the original Arrow type based on type_tag."""
    import pyarrow as pa

    if type_tag in (ARROW_TYPE_TABLE, ARROW_TYPE_PANDAS_DATAFRAME):
        return table  # Table stays as Table; pandas-converted also comes back as Table
    if type_tag == ARROW_TYPE_RECORD_BATCH:
        batches = table.to_batches()
        if len(batches) == 1:
            return batches[0]
        # Multiple batches: combine into single batch
        return pa.Table.from_batches(batches).combine_chunks().to_batches()[0]
    if type_tag == ARROW_TYPE_ARRAY:
        # Single-column table -> extract the column as Array
        return table.column(0).combine_chunks()
    if type_tag == ARROW_TYPE_CHUNKED_ARRAY:
        return table.column(0)
    msg = f"Unknown Arrow type tag: {type_tag}"
    raise ValueError(msg)


def convert_pandas_to_arrow(obj: object) -> tuple[object, bool]:
    """If obj is a pandas DataFrame and pyarrow is available, convert to Arrow Table.

    Returns (converted_obj, was_pandas). If not a DataFrame or pyarrow unavailable,
    returns (obj, False) unchanged.
    """
    if not has_arrow():
        return obj, False
    try:
        import pandas as pd
    except ImportError:
        return obj, False
    if isinstance(obj, pd.DataFrame):
        import pyarrow as pa

        return pa.Table.from_pandas(obj), True
    return obj, False
