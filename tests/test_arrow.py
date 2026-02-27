"""Tests for PyArrow zero-copy shared memory support."""

from __future__ import annotations

import pytest

pa = pytest.importorskip("pyarrow")


class TestArrowUtils:
    """Tests for _arrow_utils.py utility functions."""

    def test_has_arrow_returns_true(self):
        from fastshare._arrow_utils import has_arrow

        assert has_arrow() is True

    def test_is_arrow_type_table(self):
        from fastshare._arrow_utils import is_arrow_type

        assert is_arrow_type(pa.table({"x": [1, 2, 3]})) is True

    def test_is_arrow_type_record_batch(self):
        from fastshare._arrow_utils import is_arrow_type

        assert is_arrow_type(pa.record_batch([pa.array([1, 2])], names=["x"])) is True

    def test_is_arrow_type_array(self):
        from fastshare._arrow_utils import is_arrow_type

        assert is_arrow_type(pa.array([1, 2, 3])) is True

    def test_is_arrow_type_chunked_array(self):
        from fastshare._arrow_utils import is_arrow_type

        assert is_arrow_type(pa.chunked_array([[1, 2], [3, 4]])) is True

    def test_is_arrow_type_non_arrow(self):
        from fastshare._arrow_utils import is_arrow_type

        assert is_arrow_type("not arrow") is False
        assert is_arrow_type([1, 2, 3]) is False
        assert is_arrow_type(42) is False

    def test_get_arrow_type_tag(self):
        from fastshare._arrow_utils import (
            ARROW_TYPE_ARRAY,
            ARROW_TYPE_CHUNKED_ARRAY,
            ARROW_TYPE_RECORD_BATCH,
            ARROW_TYPE_TABLE,
            get_arrow_type_tag,
        )

        assert get_arrow_type_tag(pa.table({"x": [1]})) == ARROW_TYPE_TABLE
        assert (
            get_arrow_type_tag(pa.record_batch([pa.array([1])], names=["x"]))
            == ARROW_TYPE_RECORD_BATCH
        )
        assert get_arrow_type_tag(pa.array([1])) == ARROW_TYPE_ARRAY
        assert get_arrow_type_tag(pa.chunked_array([[1]])) == ARROW_TYPE_CHUNKED_ARRAY

    def test_get_arrow_type_tag_unsupported(self):
        from fastshare._arrow_utils import get_arrow_type_tag

        with pytest.raises(TypeError, match="Unsupported Arrow type"):
            get_arrow_type_tag("not arrow")

    def test_convert_pandas_to_arrow_dataframe(self):
        pd = pytest.importorskip("pandas")
        from fastshare._arrow_utils import convert_pandas_to_arrow

        df = pd.DataFrame({"x": [1, 2, 3]})
        result, was_pandas = convert_pandas_to_arrow(df)
        assert was_pandas is True
        assert isinstance(result, pa.Table)

    def test_convert_pandas_to_arrow_non_dataframe(self):
        from fastshare._arrow_utils import convert_pandas_to_arrow

        obj = {"not": "pandas"}
        result, was_pandas = convert_pandas_to_arrow(obj)
        assert was_pandas is False
        assert result is obj

    def test_restore_arrow_type_table(self):
        from fastshare._arrow_utils import ARROW_TYPE_TABLE, restore_arrow_type

        table = pa.table({"x": [1, 2, 3]})
        result = restore_arrow_type(table, ARROW_TYPE_TABLE)
        assert isinstance(result, pa.Table)
        assert result.equals(table)

    def test_restore_arrow_type_record_batch(self):
        from fastshare._arrow_utils import ARROW_TYPE_RECORD_BATCH, restore_arrow_type

        table = pa.table({"x": [1, 2, 3]})
        result = restore_arrow_type(table, ARROW_TYPE_RECORD_BATCH)
        assert isinstance(result, pa.RecordBatch)

    def test_restore_arrow_type_array(self):
        from fastshare._arrow_utils import ARROW_TYPE_ARRAY, restore_arrow_type

        table = pa.table({"_": [1, 2, 3]})
        result = restore_arrow_type(table, ARROW_TYPE_ARRAY)
        assert isinstance(result, pa.Array)

    def test_restore_arrow_type_chunked_array(self):
        from fastshare._arrow_utils import ARROW_TYPE_CHUNKED_ARRAY, restore_arrow_type

        table = pa.table({"_": [1, 2, 3]})
        result = restore_arrow_type(table, ARROW_TYPE_CHUNKED_ARRAY)
        assert isinstance(result, pa.ChunkedArray)


class TestArrowEstimator:
    """Tests for Arrow size estimation."""

    def test_table_size(self):
        from fastshare._estimator import estimate_size

        table = pa.table({"x": list(range(10000))})
        size = estimate_size(table)
        assert size == table.nbytes
        assert size > 0

    def test_record_batch_size(self):
        from fastshare._estimator import estimate_size

        batch = pa.record_batch([pa.array(list(range(10000)))], names=["x"])
        size = estimate_size(batch)
        assert size == batch.nbytes

    def test_array_size(self):
        from fastshare._estimator import estimate_size

        arr = pa.array(list(range(10000)))
        size = estimate_size(arr)
        assert size == arr.nbytes

    def test_chunked_array_size(self):
        from fastshare._estimator import estimate_size

        ca = pa.chunked_array([list(range(5000)), list(range(5000))])
        size = estimate_size(ca)
        assert size == ca.nbytes


class TestArrowSerializer:
    """Tests for Arrow IPC serialization via _serializer.py."""

    def test_table_round_trip(self):
        from fastshare._arrow_utils import ARROW_TYPE_TABLE
        from fastshare._serializer import deserialize_from_block, serialize_arrow_to_block

        table = pa.table({"x": [1, 2, 3], "y": ["a", "b", "c"]})
        handle = serialize_arrow_to_block(table, ARROW_TYPE_TABLE)
        result = deserialize_from_block(handle)
        assert isinstance(result, pa.Table)
        assert result.equals(table)

    def test_record_batch_round_trip(self):
        from fastshare._arrow_utils import ARROW_TYPE_RECORD_BATCH
        from fastshare._serializer import deserialize_from_block, serialize_arrow_to_block

        batch = pa.record_batch([pa.array([10, 20, 30])], names=["val"])
        handle = serialize_arrow_to_block(batch, ARROW_TYPE_RECORD_BATCH)
        result = deserialize_from_block(handle)
        assert isinstance(result, pa.RecordBatch)
        assert result.equals(batch)

    def test_array_round_trip(self):
        from fastshare._arrow_utils import ARROW_TYPE_ARRAY
        from fastshare._serializer import deserialize_from_block, serialize_arrow_to_block

        arr = pa.array([100, 200, 300])
        handle = serialize_arrow_to_block(arr, ARROW_TYPE_ARRAY)
        result = deserialize_from_block(handle)
        assert isinstance(result, pa.Array)
        assert result.equals(arr)

    def test_chunked_array_round_trip(self):
        from fastshare._arrow_utils import ARROW_TYPE_CHUNKED_ARRAY
        from fastshare._serializer import deserialize_from_block, serialize_arrow_to_block

        ca = pa.chunked_array([[1, 2], [3, 4]])
        handle = serialize_arrow_to_block(ca, ARROW_TYPE_CHUNKED_ARRAY)
        result = deserialize_from_block(handle)
        assert isinstance(result, pa.ChunkedArray)
        assert result.equals(ca)

    def test_pickle_path_unchanged(self):
        """Existing pickle path still works after Arrow IPC additions."""
        from fastshare._serializer import deserialize_from_block, serialize_to_block

        obj = {"key": [1, 2, 3], "nested": {"a": "b"}}
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_flags_byte_arrow(self):
        from fastshare._arrow_utils import ARROW_TYPE_TABLE
        from fastshare._serializer import (
            FLAG_ARROW_IPC,
            serialize_arrow_to_block,
            unpack_header,
        )

        table = pa.table({"x": [1, 2, 3]})
        handle = serialize_arrow_to_block(table, ARROW_TYPE_TABLE)
        _pickle_size, _buffer_sizes, flags, _header_size = unpack_header(handle.buf)
        assert flags & FLAG_ARROW_IPC, "Arrow IPC flag not set in header"

    def test_flags_byte_pickle(self):
        from fastshare._serializer import FLAG_ARROW_IPC, serialize_to_block, unpack_header

        handle = serialize_to_block({"x": 1})
        _pickle_size, _buffer_sizes, flags, _header_size = unpack_header(handle.buf)
        assert not (flags & FLAG_ARROW_IPC), "Arrow IPC flag should not be set for pickle"


class TestArrowWriteReadAPI:
    """Tests for write/read public API with Arrow objects."""

    def test_write_read_table(self):
        from fastshare import read, write

        table = pa.table(
            {"x": list(range(200000)), "y": [float(i) for i in range(200000)]}
        )
        token = write(table)
        assert token.startswith("FSHR:shm:")
        result = read(token)
        assert isinstance(result, pa.Table)
        assert result.equals(table)

    def test_write_read_record_batch(self):
        from fastshare import read, write

        batch = pa.record_batch([pa.array(list(range(200000)))], names=["x"])
        token = write(batch)
        assert token.startswith("FSHR:shm:")
        result = read(token)
        assert isinstance(result, pa.RecordBatch)

    def test_write_read_array(self):
        from fastshare import read, write

        arr = pa.array(list(range(200000)))
        token = write(arr)
        assert token.startswith("FSHR:shm:")
        result = read(token)
        assert isinstance(result, pa.Array)

    def test_write_read_chunked_array(self):
        from fastshare import read, write

        ca = pa.chunked_array([list(range(100000)), list(range(100000))])
        token = write(ca)
        assert token.startswith("FSHR:shm:")
        result = read(token)
        assert isinstance(result, pa.ChunkedArray)

    def test_small_arrow_uses_pickle(self):
        from fastshare import write

        small = pa.table({"x": [1, 2, 3]})
        token = write(small)
        assert token.startswith("FSHR:pkl:"), f"Small Arrow should use pickle, got {token[:20]}"

    def test_pandas_auto_convert(self):
        pd = pytest.importorskip("pandas")
        from fastshare import read, write

        df = pd.DataFrame({"a": list(range(200000)), "b": [1.0] * 200000})
        token = write(df)
        assert token.startswith("FSHR:shm:")
        result = read(token)
        assert isinstance(result, pa.Table), "Pandas DataFrame should come back as Arrow Table"

    def test_pandas_small_uses_pickle(self):
        pd = pytest.importorskip("pandas")
        from fastshare import write

        df = pd.DataFrame({"x": [1, 2, 3]})
        token = write(df)
        assert token.startswith("FSHR:pkl:")

    def test_threshold_respected(self):
        from fastshare import write

        # With high threshold, even large Arrow objects use pickle
        table = pa.table({"x": list(range(200000))})
        token = write(table, threshold=100_000_000)
        assert token.startswith("FSHR:pkl:")


class TestArrowSharedData:
    """Tests for SharedData with Arrow objects."""

    def test_shared_data_table(self):
        from fastshare import SharedData

        table = pa.table(
            {"x": list(range(100000)), "y": [float(i) for i in range(100000)]}
        )
        with SharedData(table) as sd:
            assert sd.name.startswith("FSHR_")
            loaded = SharedData.load(sd.name)
            assert isinstance(loaded, pa.Table)
            assert loaded.equals(table)
        SharedData.clear_cache()

    def test_shared_data_record_batch(self):
        from fastshare import SharedData

        batch = pa.record_batch([pa.array(list(range(100000)))], names=["x"])
        with SharedData(batch) as sd:
            loaded = SharedData.load(sd.name)
            assert isinstance(loaded, pa.RecordBatch)
        SharedData.clear_cache()

    def test_shared_data_caching(self):
        from fastshare import SharedData

        table = pa.table({"x": list(range(100000))})
        with SharedData(table) as sd:
            first = SharedData.load(sd.name)
            second = SharedData.load(sd.name)
            assert first is second, "Cached loads should return same object"
        SharedData.clear_cache()

    def test_shared_data_arrow_from_pandas(self):
        """SharedData with an Arrow Table converted from pandas."""
        pd = pytest.importorskip("pandas")
        from fastshare import SharedData

        df = pd.DataFrame({"a": list(range(100000)), "b": [1.0] * 100000})
        # User converts to Arrow first for SharedData (auto-convert is write() only)
        table = pa.Table.from_pandas(df)
        with SharedData(table) as sd:
            loaded = SharedData.load(sd.name)
            assert isinstance(loaded, pa.Table)
        SharedData.clear_cache()
