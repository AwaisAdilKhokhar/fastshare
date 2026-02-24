"""CLI integration tests for the fastshare cleanup command."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from fastshare._cleanup import CleanupResult
from fastshare.__main__ import main


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_main(*argv: str) -> int:
    """Run main() with the given argv, returning the exit code.

    Captures SystemExit so tests can inspect the exit code.
    """
    with patch("sys.argv", ["fastshare", *argv]):
        try:
            main()
            return 0  # main() returned normally (no sys.exit call)
        except SystemExit as exc:
            return exc.code if exc.code is not None else 0


# ---------------------------------------------------------------------------
# TestCLIArgumentParsing
# ---------------------------------------------------------------------------


class TestCLIArgumentParsing:
    """Tests for argument parsing behavior."""

    @patch("fastshare.__main__.cleanup")
    def test_cleanup_command_accepted(self, mock_cleanup):
        """Invoking main() with cleanup --dry-run runs without error."""
        mock_cleanup.return_value = CleanupResult()
        code = _run_main("cleanup", "--dry-run")
        assert code == 0
        mock_cleanup.assert_called_once_with(dry_run=True)

    def test_no_command_shows_help(self, capsys):
        """Invoking with no args prints help and exits 0."""
        code = _run_main()
        assert code == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower() or "fastshare" in captured.out

    def test_verbose_quiet_mutually_exclusive(self):
        """--verbose and --quiet together should be rejected by argparse."""
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["fastshare", "cleanup", "--verbose", "--quiet"]):
                main()
        assert exc_info.value.code == 2  # argparse error exit code


# ---------------------------------------------------------------------------
# TestCLIOutput
# ---------------------------------------------------------------------------


class TestCLIOutput:
    """Tests for CLI output formatting in different modes."""

    @patch("fastshare.__main__.cleanup")
    def test_no_blocks_found_message(self, mock_cleanup, capsys):
        """When no blocks found, output is 'No orphaned blocks found'."""
        mock_cleanup.return_value = CleanupResult()
        _run_main("cleanup")
        captured = capsys.readouterr()
        assert "No orphaned blocks found" in captured.out

    @patch("fastshare.__main__.cleanup")
    def test_default_output_lists_blocks(self, mock_cleanup, capsys):
        """Default mode lists each cleaned block name."""
        mock_cleanup.return_value = CleanupResult(
            cleaned=["FSHR_abcd1234", "FSHR_efgh5678"]
        )
        _run_main("cleanup")
        captured = capsys.readouterr()
        assert "Cleaned: FSHR_abcd1234" in captured.out
        assert "Cleaned: FSHR_efgh5678" in captured.out
        assert "2 block(s) cleaned" in captured.out

    @patch("fastshare.__main__.cleanup")
    def test_dry_run_output(self, mock_cleanup, capsys):
        """Dry run uses 'Would clean:' prefix."""
        mock_cleanup.return_value = CleanupResult(
            cleaned=["FSHR_abcd1234"]
        )
        _run_main("cleanup", "--dry-run")
        captured = capsys.readouterr()
        assert "Would clean: FSHR_abcd1234" in captured.out
        assert "1 block(s) found" in captured.out

    @patch("fastshare.__main__.cleanup")
    def test_quiet_mode_summary_only(self, mock_cleanup, capsys):
        """Quiet mode shows only the count line."""
        mock_cleanup.return_value = CleanupResult(
            cleaned=["FSHR_a1", "FSHR_b2"]
        )
        _run_main("cleanup", "--quiet")
        captured = capsys.readouterr()
        # Should just be the summary count
        assert "2 block(s) cleaned" in captured.out
        # Should NOT contain per-block detail
        assert "Cleaned:" not in captured.out

    @patch("fastshare.__main__.cleanup")
    def test_failed_blocks_to_stderr(self, mock_cleanup, capsys):
        """Failed blocks are reported to stderr."""
        mock_cleanup.return_value = CleanupResult(
            failed=[("FSHR_bad", "Permission denied")]
        )
        _run_main("cleanup")
        captured = capsys.readouterr()
        assert "FAILED: FSHR_bad (Permission denied)" in captured.err

    @patch("fastshare.__main__.cleanup")
    def test_skipped_blocks_shown(self, mock_cleanup, capsys):
        """Skipped (in-use) blocks are shown in output."""
        mock_cleanup.return_value = CleanupResult(
            cleaned=["FSHR_orphan"],
            skipped=["FSHR_mine"],
        )
        _run_main("cleanup")
        captured = capsys.readouterr()
        assert "Skipped (in use): FSHR_mine" in captured.out


# ---------------------------------------------------------------------------
# TestCLIExitCodes
# ---------------------------------------------------------------------------


class TestCLIExitCodes:
    """Tests for CLI exit code behavior."""

    @patch("fastshare.__main__.cleanup")
    def test_exit_0_on_success(self, mock_cleanup):
        """Exit code 0 when cleanup succeeds with blocks cleaned."""
        mock_cleanup.return_value = CleanupResult(cleaned=["FSHR_a1"])
        code = _run_main("cleanup")
        assert code == 0

    @patch("fastshare.__main__.cleanup")
    def test_exit_0_when_no_blocks(self, mock_cleanup):
        """Exit code 0 when no orphaned blocks found."""
        mock_cleanup.return_value = CleanupResult()
        code = _run_main("cleanup")
        assert code == 0

    @patch("fastshare.__main__.cleanup")
    def test_exit_1_on_failures(self, mock_cleanup):
        """Exit code 1 when cleanup has failed blocks."""
        mock_cleanup.return_value = CleanupResult(
            failed=[("FSHR_bad", "Permission denied")]
        )
        code = _run_main("cleanup")
        assert code == 1


# ---------------------------------------------------------------------------
# TestPublicAPIExport
# ---------------------------------------------------------------------------


class TestPublicAPIExport:
    """Tests for public API export of cleanup function."""

    def test_cleanup_importable(self):
        """cleanup is importable from top-level fastshare package."""
        from fastshare import cleanup as cleanup_fn

        assert callable(cleanup_fn)

    def test_cleanup_in_all(self):
        """cleanup is listed in fastshare.__all__."""
        import fastshare

        assert "cleanup" in fastshare.__all__
