"""Write-once broadcast context manager for shared memory.

Provides :class:`SharedData`, the primary user-facing abstraction for the
multi-worker broadcast pattern.  Parents write an object once via
``with SharedData(obj) as sd:``, pass ``sd.name`` to workers, and workers
call ``SharedData.load(name)`` for a cached zero-copy view.
"""

from __future__ import annotations

from fastshare._errors import BlockNotFoundError, FastShareError  # noqa: F401
from fastshare._numpy_utils import enforce_readonly
from fastshare._registry import BlockHandle, attach
from fastshare._serializer import deserialize_from_block, serialize_to_block

# Module-level cache: {block_name: deserialized_object}
# Each process gets its own copy after fork/spawn.
_cache: dict[str, object] = {}


class SharedData:
    """Write-once broadcast context manager for shared memory.

    Parent side::

        with SharedData(large_obj) as sd:
            # sd.name is the FSHR_ block name to pass to workers
            pool.map(worker_fn, [(sd.name, i) for i in range(N)])
        # Block automatically unlinked here

    Worker side::

        def worker_fn(args):
            name, idx = args
            data = SharedData.load(name)  # Cached zero-copy view

    .. warning::

        All workers must call :meth:`load` **before** the parent exits the
        ``with`` block.  On POSIX, ``__exit__`` unlinks the block name
        immediately; existing mappings remain valid but new attachments will
        raise :class:`~fastshare.BlockNotFoundError`.
    """

    def __init__(self, obj: object) -> None:
        self._obj = obj
        self._handle: BlockHandle | None = None
        self._entered = False

    def __enter__(self) -> SharedData:
        if self._entered:
            raise RuntimeError("SharedData does not support re-entry")
        self._entered = True
        # Serialization failures (PicklingError, AllocationError) propagate immediately
        self._handle = serialize_to_block(self._obj)
        self._obj = None  # Release original object reference
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._handle is not None:
            self._handle.close()  # Triggers unlink via finalizer
            self._handle = None
        return None  # Do not suppress exceptions

    @property
    def name(self) -> str:
        """The FSHR-prefixed block name for passing to workers."""
        if self._handle is None:
            raise RuntimeError("SharedData not entered or already exited")
        return self._handle.name

    @property
    def size(self) -> int:
        """The size of the shared memory block in bytes."""
        if self._handle is None:
            raise RuntimeError("SharedData not entered or already exited")
        return self._handle.size

    @classmethod
    def load(cls, name: str) -> object:
        """Load a shared object by block name, with per-process caching.

        Workers call this classmethod with the block name received from the
        parent process.  The first call attaches to shared memory and
        deserializes the object; subsequent calls return the cached instance.

        Args:
            name: The FSHR-prefixed block name (from ``sd.name``).

        Returns:
            The deserialized object (readonly if it contains NumPy arrays).

        Raises:
            TypeError: If *name* is not a string.
            FastShareError: If *name* does not start with ``"FSHR_"``.
            BlockNotFoundError: If the block has been unlinked or does not exist.
        """
        if not isinstance(name, str):
            raise TypeError(f"name must be a string, got {type(name).__name__}")
        if name in _cache:
            return _cache[name]
        if not name.startswith("FSHR_"):
            raise FastShareError(f"Invalid block name: {name!r}")
        handle = attach(name)  # Raises BlockNotFoundError if expired
        obj = deserialize_from_block(handle)
        enforce_readonly(obj)
        _cache[name] = obj
        return obj

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the per-process object cache.

        Call this in long-running workers between batches to free memory
        held by cached deserialized objects.
        """
        _cache.clear()
