"""fastshare - Zero-copy shared memory transfer of large Python objects."""

from __future__ import annotations

import logging
from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fastshare")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for uninstalled development

# Silent by default: user must configure logging to see output
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Exception hierarchy (available from Phase 1)
from fastshare._errors import AllocationError, BlockNotFoundError, FastShareError

# Ensure registry atexit handler is registered on first import
from fastshare import _registry as _registry  # noqa: F401

# Public API -- write/read (Phase 2)
from fastshare._api import read, write

# Public API -- SharedData broadcast (Phase 3)
from fastshare._data import SharedData

# Public API -- Cleanup (Phase 4)
from fastshare._cleanup import CleanupResult, cleanup

__all__ = [
    "__version__",
    "FastShareError",
    "AllocationError",
    "BlockNotFoundError",
    "write",
    "read",
    "SharedData",
    "cleanup",
    "CleanupResult",
]
