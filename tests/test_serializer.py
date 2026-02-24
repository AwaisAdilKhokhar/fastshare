"""Tests for fastshare._serializer: binary header and pickle protocol 5 round-trips."""

from __future__ import annotations

import struct

import pytest

from fastshare._errors import FastShareError
from fastshare._serializer import (
    _HEADER_BASE_SIZE,
    _HEADER_MAGIC,
    _HEADER_VERSION,
    deserialize_from_block,
    pack_header,
    serialize_to_block,
    unpack_header,
)


# ---------------------------------------------------------------------------
# pack_header / unpack_header round-trip
# ---------------------------------------------------------------------------


class TestHeader:
    def test_zero_buffers_header_size(self) -> None:
        header = pack_header(pickle_size=100, buffer_sizes=[])
        assert len(header) == _HEADER_BASE_SIZE  # exactly 16 bytes

    def test_zero_buffers_round_trip(self) -> None:
        header = pack_header(pickle_size=512, buffer_sizes=[], flags=0)
        pickle_size, buffer_sizes, flags, total_size = unpack_header(header)
        assert pickle_size == 512
        assert buffer_sizes == []
        assert flags == 0
        assert total_size == _HEADER_BASE_SIZE

    def test_two_buffers_round_trip(self) -> None:
        sizes = [8_000_000, 16_000_000]
        header = pack_header(pickle_size=1024, buffer_sizes=sizes, flags=1)
        pickle_size, buffer_sizes, flags, total_size = unpack_header(header)
        assert pickle_size == 1024
        assert buffer_sizes == sizes
        assert flags == 1
        assert total_size == _HEADER_BASE_SIZE + 8 * 2

    def test_many_buffers_round_trip(self) -> None:
        sizes = [100 * i for i in range(10)]
        header = pack_header(pickle_size=256, buffer_sizes=sizes)
        pickle_size, buffer_sizes, flags, total_size = unpack_header(header)
        assert pickle_size == 256
        assert buffer_sizes == sizes
        assert total_size == _HEADER_BASE_SIZE + 8 * 10

    def test_invalid_magic_raises(self) -> None:
        # Build a valid header, then corrupt the magic bytes
        header = bytearray(pack_header(pickle_size=100, buffer_sizes=[]))
        header[0:4] = b"XXXX"
        with pytest.raises(FastShareError, match="bad magic"):
            unpack_header(bytes(header))

    def test_invalid_version_raises(self) -> None:
        # Build a valid header, then set version to 99
        header = bytearray(pack_header(pickle_size=100, buffer_sizes=[]))
        header[4] = 99
        with pytest.raises(FastShareError, match="Unsupported block version: 99"):
            unpack_header(bytes(header))

    def test_header_magic_and_version_values(self) -> None:
        header = pack_header(pickle_size=0, buffer_sizes=[])
        magic, version = struct.unpack("<4sB", header[:5])
        assert magic == _HEADER_MAGIC
        assert version == _HEADER_VERSION


# ---------------------------------------------------------------------------
# serialize_to_block / deserialize_from_block round-trip
# ---------------------------------------------------------------------------


class TestSerializerRoundTrip:
    def test_plain_dict(self) -> None:
        obj = {"key": "value"}
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_plain_list(self) -> None:
        obj = [1, 2, 3]
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_bytes_object(self) -> None:
        obj = b"x" * 10_000
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_nested_dict(self) -> None:
        obj = {"a": [1, 2, 3], "b": {"nested": True}, "c": "hello"}
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_none(self) -> None:
        handle = serialize_to_block(None)
        result = deserialize_from_block(handle)
        assert result is None

    def test_empty_dict(self) -> None:
        handle = serialize_to_block({})
        result = deserialize_from_block(handle)
        assert result == {}

    def test_string(self) -> None:
        obj = "hello world"
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result == obj

    def test_integer(self) -> None:
        handle = serialize_to_block(42)
        result = deserialize_from_block(handle)
        assert result == 42


# ---------------------------------------------------------------------------
# NumPy round-trip tests
# ---------------------------------------------------------------------------


class TestSerializerNumpy:
    np = pytest.importorskip("numpy")

    def test_numpy_array_round_trip(self) -> None:
        np = self.np
        arr = np.arange(100, dtype=np.float64)
        handle = serialize_to_block(arr)
        result = deserialize_from_block(handle)
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.float64
        assert result.shape == (100,)
        np.testing.assert_array_equal(result, arr)

    def test_large_numpy_array(self) -> None:
        np = self.np
        arr = np.zeros(1000, dtype=np.float64)
        handle = serialize_to_block(arr)
        result = deserialize_from_block(handle)
        np.testing.assert_array_equal(result, arr)

    def test_numpy_2d_array(self) -> None:
        np = self.np
        arr = np.arange(24, dtype=np.int32).reshape(4, 6)
        handle = serialize_to_block(arr)
        result = deserialize_from_block(handle)
        assert result.shape == (4, 6)
        assert result.dtype == np.int32
        np.testing.assert_array_equal(result, arr)

    def test_nested_structure_with_numpy(self) -> None:
        np = self.np
        obj = {"arr": np.zeros(100), "meta": "test"}
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        assert result["meta"] == "test"
        np.testing.assert_array_equal(result["arr"], np.zeros(100))

    def test_multiple_arrays_in_structure(self) -> None:
        np = self.np
        obj = {
            "a": np.arange(50, dtype=np.float32),
            "b": np.ones(30, dtype=np.float64),
        }
        handle = serialize_to_block(obj)
        result = deserialize_from_block(handle)
        np.testing.assert_array_equal(result["a"], obj["a"])
        np.testing.assert_array_equal(result["b"], obj["b"])

    def test_numpy_array_data_integrity(self) -> None:
        """Verify data integrity with non-trivial values."""
        np = self.np
        arr = np.array([3.14, 2.718, 1.618, 0.577, 1.414], dtype=np.float64)
        handle = serialize_to_block(arr)
        result = deserialize_from_block(handle)
        np.testing.assert_array_equal(result, arr)
