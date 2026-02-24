"""Shared pytest configuration and fixtures for fastshare tests."""

from __future__ import annotations

import multiprocessing as mp
import traceback

import pytest


@pytest.fixture(autouse=True)
def cleanup_registry():
    """Auto-cleanup all shared memory blocks after each test.

    Yields control to the test, then iterates the registry and closes
    all remaining handles to prevent shared memory leaks between tests.
    """
    from fastshare._registry import _registry

    yield

    for name in list(_registry):
        handles = _registry.get(name, [])
        for handle in list(handles):
            try:
                handle.close()
            except Exception:  # noqa: BLE001
                pass


def _worker(queue, func, a, kw):
    """Worker target for run_in_child. Module-level for spawn picklability."""
    try:
        result = func(*a, **kw)
        queue.put(("ok", result))
    except Exception as exc:
        queue.put(("error", (type(exc).__name__, str(exc), traceback.format_exc())))


def run_in_child(start_method: str, fn, *args, **kwargs):
    """Run fn(*args, **kwargs) in a child process and return the result.

    Uses multiprocessing.get_context() for per-test start method selection.
    Raises RuntimeError in parent if child raises or exits non-zero.
    """
    ctx = mp.get_context(start_method)
    q = ctx.Queue()

    p = ctx.Process(target=_worker, args=(q, fn, args, kwargs))
    p.start()
    p.join(timeout=60)

    if p.is_alive():
        p.terminate()
        p.join(timeout=5)
        if p.is_alive():
            p.kill()
        raise RuntimeError("Child process timed out after 60 seconds")

    if p.exitcode != 0 and q.empty():
        raise RuntimeError(f"Child process exited with code {p.exitcode}")

    status, payload = q.get(timeout=10)
    if status == "error":
        exc_name, exc_msg, exc_tb = payload
        raise RuntimeError(f"Child process raised {exc_name}: {exc_msg}\n{exc_tb}")
    return payload


@pytest.fixture
def spawn_child():
    """Fixture providing a function to run callables in a spawn child process."""

    def _run(fn, *args, **kwargs):
        return run_in_child("spawn", fn, *args, **kwargs)

    return _run


@pytest.fixture
def fork_child():
    """Fixture providing a function to run callables in a fork child process."""

    def _run(fn, *args, **kwargs):
        return run_in_child("fork", fn, *args, **kwargs)

    return _run
