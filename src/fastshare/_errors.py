"""Custom exception hierarchy for fastshare."""

from __future__ import annotations


class FastShareError(Exception):
    """Base exception for all fastshare errors."""


class AllocationError(FastShareError):
    """Raised when shared memory allocation fails."""


class BlockNotFoundError(FastShareError, KeyError):
    """Raised when a shared memory block cannot be found by name."""
