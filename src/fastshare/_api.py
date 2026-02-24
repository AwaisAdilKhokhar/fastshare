"""Public write/read API for fastshare.

Provides :func:`write` (serialize an object to a fastshare token) and
:func:`read` (reconstruct an object from a token).  The write path uses
a size heuristic to choose between shared memory (fast, zero-copy for
large objects) and pickle-to-base64 (portable fallback for small
objects or when shared memory allocation fails).
"""

from __future__ import annotations

import base64
import logging
import pickle
import warnings

from fastshare._errors import AllocationError, BlockNotFoundError, FastShareError
from fastshare._estimator import estimate_size
from fastshare._numpy_utils import check_contiguity, enforce_readonly
from fastshare._registry import attach
from fastshare._serializer import deserialize_from_block, serialize_to_block

logger = logging.getLogger("fastshare")


def write(obj: object, *, threshold: int = 1_000_000) -> str:
    """Serialize *obj* and return a fastshare token string.

    Objects below *threshold* bytes (estimated) are pickled and encoded
    as a base64 token.  Larger objects are written into shared memory
    for zero-copy transfer between processes.

    If shared memory allocation fails, the function falls back to
    pickle with a :class:`UserWarning`.

    Args:
        obj: Any picklable Python object.
        threshold: Size in bytes below which pickle fallback is used.
            Defaults to 1 MB.

    Returns:
        A ``"FSHR:"``-prefixed token string.

    Raises:
        pickle.PicklingError: If *obj* cannot be pickled.
    """
    # 1. Contiguity check (NumPy arrays)
    obj = check_contiguity(obj)

    # 2. Size estimation
    estimated_size = estimate_size(obj)

    # 3. Threshold decision -- small objects go via pickle fallback
    if estimated_size < threshold:
        logger.debug(
            "Object below threshold (%d < %d), using pickle fallback",
            estimated_size,
            threshold,
        )
        return _pickle_token(obj)

    # 4. Shared memory path -- large objects
    try:
        handle = serialize_to_block(obj)
        return "FSHR:shm:" + handle.name
    except (OSError, AllocationError) as e:
        warnings.warn(
            f"Shared memory allocation failed: {e}. Falling back to pickle.",
            UserWarning,
            stacklevel=2,
        )
        return _pickle_token(obj)


def read(token: str, *, readonly: bool = True) -> object:
    """Reconstruct an object from a fastshare *token*.

    Args:
        token: A ``"FSHR:"``-prefixed token returned by :func:`write`.
        readonly: If ``True`` (default), all NumPy arrays in the result
            have ``writeable=False``.  Set to ``False`` to allow
            in-place mutation.

    Returns:
        The reconstructed Python object.

    Raises:
        FastShareError: If the token is invalid, the shared memory block
            is missing, or the token mode is unknown.
    """
    # 1. Token validation
    if not token.startswith("FSHR:"):
        msg = f"Invalid fastshare token: {token!r}"
        raise FastShareError(msg)

    # 2. Parse token
    parts = token.split(":", maxsplit=2)
    if len(parts) != 3:  # noqa: PLR2004
        msg = f"Invalid fastshare token: {token!r}"
        raise FastShareError(msg)
    mode = parts[1]
    payload = parts[2]

    # 3. Pickle path
    if mode == "pkl":
        data = base64.urlsafe_b64decode(payload.encode("ascii"))
        obj = pickle.loads(data)  # noqa: S301
        if readonly:
            enforce_readonly(obj)
        return obj

    # 4. Shared memory path
    if mode == "shm":
        block_name = payload
        try:
            handle = attach(block_name)
        except BlockNotFoundError as exc:
            msg = f"Shared memory block not found: {block_name!r}"
            raise FastShareError(msg) from exc
        obj = deserialize_from_block(handle)
        if readonly:
            enforce_readonly(obj)
        return obj

    # 5. Unknown mode
    msg = f"Unknown token mode: {mode!r}"
    raise FastShareError(msg)


def _pickle_token(obj: object) -> str:
    """Pickle *obj* and return a FSHR:pkl: token."""
    data = pickle.dumps(obj, protocol=5)
    return "FSHR:pkl:" + base64.urlsafe_b64encode(data).decode("ascii")
