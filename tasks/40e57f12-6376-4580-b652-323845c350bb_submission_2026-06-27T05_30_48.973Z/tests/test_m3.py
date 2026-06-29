"""Milestone 3 verifier tests for checksum export."""

from __future__ import annotations

import diffusion_ref


class TestMilestone3:
    """Checksum and report reconciliation checks."""

    def test_checksum_file_exists(self) -> None:
        """summary.checksum must be written under /app/workbook/out."""
        assert diffusion_ref.CHECKSUM.is_file()

    def test_checksum_matches_canonical_body(self) -> None:
        """summary.checksum must be sha256 of canonical summary serialization."""
        expected = diffusion_ref.expected_checksum()
        actual = diffusion_ref.CHECKSUM.read_text(encoding="utf-8").strip()
        assert actual == expected

    def test_report_checksum_matches_output(self) -> None:
        """Report checksum line must match summary.checksum."""
        assert diffusion_ref.report_checksum() == diffusion_ref.CHECKSUM.read_text(
            encoding="utf-8"
        ).strip()

    def test_canonical_body_has_no_trailing_newline(self) -> None:
        """Checksum input must not include a trailing newline."""
        body = diffusion_ref.expected_checksum_body()
        assert body
        assert not body.endswith("\n")

    def test_summary_rows_sorted_by_sweep_id(self) -> None:
        """Canonical serialization must follow sweep_id ascending order."""
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute(
                """
                SELECT sweep_id, kernel_revision, diffusion_coeff, rss
                FROM diffusion_summary
                ORDER BY sweep_id ASC
                """
            ).fetchall()
        finally:
            conn.close()
        expected = diffusion_ref.expected_summary()
        for row, exp in zip(rows, expected, strict=True):
            assert row["sweep_id"] == exp["sweep_id"]
            assert row["kernel_revision"] == exp["kernel_revision"]
