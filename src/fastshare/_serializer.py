"""Pickle protocol 5 serializer with binary header and shared memory packing.

Serializes Python objects using PEP 574 out-of-band buffers, packing the pickle
metadata stream and large data buffers into a single shared memory block with a
struct-based binary header describing the layout.
"""

from __future__ import annotations

import pickle
import struct

from fastshare._errors import FastShareError
from fastshare._registry import BlockHandle, allocate

# ---------------------------------------------------------------------------
# Binary header format
# ---------------------------------------------------------------------------
# [HEADER: 16 + 8*num_buffers bytes]
#   magic        (4 bytes): b"FSHR"
#   version      (1 byte):  0x01
#   flags        (1 byte):  bit 0 = has_numpy_buffers (reserved)
#   num_buffers  (2 bytes): uint16 LE
#   pickle_size  (8 bytes): uint64 LE
#   buffer_sizes (8 bytes each): uint64 LE per buffer
#
# [PICKLE DATA: pickle_size bytes]
# [BUFFER 0: buffer_sizes[0] bytes]
# [BUFFER 1: buffer_sizes[1] bytes]
# ...

_HEADER_MAGIC = b"FSHR"
_HEADER_VERSION = 1
_HEADER_BASE_FORMAT = "<4sBBHQ"  # magic, version, flags, num_buffers, pickle_size
_HEADER_BASE_SIZE = struct.calcsize(_HEADER_BASE_FORMAT)  # 16 bytes


def pack_header(pickle_size: int, buffer_sizes: list[int], flags: int = 0) -> bytes:
    """Pack the binary header describing a shared memory block layout.

    Args:
        pickle_size: Size of the pickle data stream in bytes.
        buffer_sizes: Sizes of each out-of-band buffer in bytes.
        flags: Reserved flags byte (default 0).

    Returns:
        The packed header as bytes.
    """
    header = struct.pack(
        _HEADER_BASE_FORMAT,
        _HEADER_MAGIC,
        _HEADER_VERSION,
        flags,
        len(buffer_sizes),
        pickle_size,
    )
    for size in buffer_sizes:
        header += struct.pack("<Q", size)
    return header


def unpack_header(buf: memoryview | bytes) -> tuple[int, list[int], int, int]:
    """Unpack a binary header from a buffer.

    Args:
        buf: The buffer (memoryview or bytes) containing the header.

    Returns:
        Tuple of ``(pickle_size, buffer_sizes, flags, header_total_size)``.

    Raises:
        FastShareError: If magic bytes are invalid or version is unsupported.
    """
    magic, version, flags, num_buffers, pickle_size = struct.unpack(
        _HEADER_BASE_FORMAT, buf[:_HEADER_BASE_SIZE]
    )
    if magic != _HEADER_MAGIC:
        msg = "Invalid block header: bad magic"
        raise FastShareError(msg)
    if version != _HEADER_VERSION:
        msg = f"Unsupported block version: {version}"
        raise FastShareError(msg)

    buffer_sizes: list[int] = []
    offset = _HEADER_BASE_SIZE
    for _ in range(num_buffers):
        (size,) = struct.unpack("<Q", buf[offset : offset + 8])
        buffer_sizes.append(size)
        offset += 8

    header_total_size = _HEADER_BASE_SIZE + 8 * num_buffers
    return pickle_size, buffer_sizes, flags, header_total_size


def serialize_to_block(obj: object) -> BlockHandle:
    """Serialize *obj* into a shared memory block using pickle protocol 5.

    Large data buffers (e.g., NumPy arrays) are extracted via
    ``buffer_callback`` and packed directly into shared memory alongside the
    pickle metadata stream.

    Args:
        obj: Any picklable Python object.

    Returns:
        A :class:`BlockHandle` (owner) wrapping the shared memory block.
    """
    buffers: list[pickle.PickleBuffer] = []
    pickle_data = pickle.dumps(obj, protocol=5, buffer_callback=buffers.append)

    pickle_size = len(pickle_data)
    # Use .raw() to get a contiguous memoryview of each buffer
    buffer_raws = [b.raw() for b in buffers]
    buffer_sizes = [len(raw) for raw in buffer_raws]

    header = pack_header(pickle_size, buffer_sizes)
    header_size = len(header)

    total_size = header_size + pickle_size + sum(buffer_sizes)
    block = allocate(total_size)

    # Write header
    block.buf[0:header_size] = header

    # Write pickle data
    offset = header_size
    block.buf[offset : offset + pickle_size] = pickle_data

    # Write each buffer directly into shared memory (zero-copy write path)
    offset += pickle_size
    for raw, size in zip(buffer_raws, buffer_sizes):
        block.buf[offset : offset + size] = raw
        offset += size

    return block


def deserialize_from_block(handle: BlockHandle, *, readonly: bool = True) -> object:
    """Deserialize an object from a shared memory block.

    The pickle metadata is extracted as bytes (small), while large data buffers
    are passed back as memoryview slices pointing directly into shared memory
    (zero-copy for NumPy array reconstruction).

    Args:
        handle: A :class:`BlockHandle` wrapping the shared memory block.
        readonly: Currently unused here; readonly enforcement happens in
            ``_api.py`` via :func:`enforce_readonly`.

    Returns:
        The reconstructed Python object.
    """
    pickle_size, buffer_sizes, _flags, header_total_size = unpack_header(handle.buf)

    # Extract pickle data as bytes (pickle.loads needs bytes, not memoryview).
    # This is the small metadata stream, not the large data buffers.
    header_end = header_total_size
    pickle_data = bytes(handle.buf[header_end : header_end + pickle_size])

    # Create memoryview slices for each buffer -- these point into shared memory.
    # NumPy arrays will be reconstructed from these slices (zero-copy).
    buffer_views: list[memoryview] = []
    offset = header_end + pickle_size
    for size in buffer_sizes:
        buffer_views.append(handle.buf[offset : offset + size])
        offset += size

    return pickle.loads(pickle_data, buffers=buffer_views)  # noqa: S301
