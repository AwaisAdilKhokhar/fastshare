"""CLI entry point for fastshare."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from fastshare import __version__
from fastshare._cleanup import cleanup


def _get_block_info(name: str) -> dict[str, str]:
    """Get size and age information for a shared memory block.

    Only available on Linux where /dev/shm provides filesystem access.

    Args:
        name: The FSHR-prefixed block name.

    Returns:
        Dict with 'size' and 'age' keys (human-readable strings),
        or empty dict if info is unavailable.
    """
    if sys.platform != "linux":
        return {}
    try:
        path = Path("/dev/shm") / name
        stat = path.stat()
        size_bytes = stat.st_size
        mtime = stat.st_mtime
    except OSError:
        return {}

    # Human-readable size
    if size_bytes < 1024:
        size_str = f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        size_str = f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    # Human-readable age
    age_seconds = time.time() - mtime
    if age_seconds < 60:
        age_str = f"{int(age_seconds)} sec"
    elif age_seconds < 3600:
        age_str = f"{int(age_seconds // 60)} min"
    elif age_seconds < 86400:
        age_str = f"{int(age_seconds // 3600)} hours"
    else:
        age_str = f"{int(age_seconds // 86400)} days"

    return {"size": size_str, "age": age_str}


def _run_cleanup(args: object) -> None:
    """Execute the cleanup command with parsed arguments.

    Args:
        args: Parsed argparse namespace with dry_run, verbose, quiet attributes.
    """
    dry_run: bool = getattr(args, "dry_run", False)
    verbose: bool = getattr(args, "verbose", False)
    quiet: bool = getattr(args, "quiet", False)

    result = cleanup(dry_run=dry_run)

    action = "found" if dry_run else "cleaned"
    prefix = "Would clean" if dry_run else "Cleaned"

    # Quiet mode: summary only
    if quiet:
        print(f"{len(result.cleaned)} block(s) {action}")
        if result.failed:
            sys.exit(1)
        sys.exit(0)

    # No blocks found at all
    if not result.cleaned and not result.failed and not result.skipped:
        print("No orphaned blocks found")
        sys.exit(0)

    # Default and verbose modes: per-block detail
    for name in result.cleaned:
        line = f"  {prefix}: {name}"
        if verbose:
            info = _get_block_info(name)
            if info:
                line += f" (size: {info['size']}, age: {info['age']})"
        print(line)

    for name, error in result.failed:
        print(f"  FAILED: {name} ({error})", file=sys.stderr)

    for name in result.skipped:
        print(f"  Skipped (in use): {name}")

    # Summary line
    print(f"\n{len(result.cleaned)} block(s) {action}, {len(result.failed)} failed")

    if result.failed:
        sys.exit(1)
    sys.exit(0)


def main() -> None:
    """Entry point for the ``fastshare`` command."""
    import argparse

    parser = argparse.ArgumentParser(prog="fastshare", description="fastshare CLI")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    # cleanup subcommand
    cleanup_parser = subparsers.add_parser(
        "cleanup",
        help="Clean up orphaned shared memory blocks",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List orphaned blocks without removing them",
    )

    # --verbose and --quiet are mutually exclusive
    output_group = cleanup_parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--verbose",
        action="store_true",
        help="Show extra detail (block sizes, ages)",
    )
    output_group.add_argument(
        "--quiet",
        action="store_true",
        help="Summary-only output (just the count)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    if args.command == "cleanup":
        _run_cleanup(args)


if __name__ == "__main__":
    main()
