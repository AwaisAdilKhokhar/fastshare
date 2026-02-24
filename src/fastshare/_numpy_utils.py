"""NumPy utility functions: contiguity check, readonly enforcement, availability detection."""

from __future__ import annotations

import warnings

# Lazy numpy availability cache
_numpy_available: bool | None = None


def has_numpy() -> bool:
    """Return True if numpy is importable, caching the result after first call."""
    global _numpy_available  # noqa: PLW0603
    if _numpy_available is None:
        try:
            import numpy as np  # noqa: F401

            _numpy_available = True
        except ImportError:
            _numpy_available = False
    return _numpy_available


def check_contiguity(obj: object) -> object:
    """Check if *obj* is a C-contiguous NumPy array; warn and copy if not.

    If numpy is available and *obj* is an ndarray that is **not** C-contiguous,
    a warning is issued and a contiguous copy is returned.  Otherwise *obj* is
    returned unchanged.
    """
    if not has_numpy():
        return obj

    import numpy as np

    if not isinstance(obj, np.ndarray):
        return obj

    if obj.flags.c_contiguous:
        return obj

    warnings.warn(
        f"Non-contiguous array detected (shape={obj.shape}, strides={obj.strides}). "
        "Copying to C-contiguous layout.",
        stacklevel=2,
    )
    return np.ascontiguousarray(obj)


def enforce_readonly(obj: object) -> object:
    """Recursively set ``writeable=False`` on all NumPy arrays in *obj*.

    Handles ``ndarray``, ``dict`` (recurse values), ``list`` and ``tuple``
    (recurse items).  All other types are returned as-is.

    Returns *obj* for chaining (arrays are modified in-place).
    """
    if not has_numpy():
        return obj

    import numpy as np

    if isinstance(obj, np.ndarray):
        obj.flags.writeable = False
    elif isinstance(obj, dict):
        for value in obj.values():
            enforce_readonly(value)
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            enforce_readonly(item)

    return obj
