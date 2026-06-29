"""Milestone 2 verifier tests for diffusion summary migration."""

from __future__ import annotations

import diffusion_ref


class TestMilestone2:
    """Summary migration checks."""

    def test_summary_row_count(self) -> None:
        """Each sweep must produce one diffusion_summary row."""
        expected = len(diffusion_ref.expected_summary())
        conn = diffusion_ref.connect()
        try:
            count = conn.execute("SELECT count(*) FROM diffusion_summary").fetchone()[0]
        finally:
            conn.close()
        assert count == expected

    def test_diffusion_coefficients(self) -> None:
        """Diffusion coefficients must follow the MSD contract."""
        expected = {
            row["sweep_id"]: row["diffusion_coeff"] for row in diffusion_ref.expected_summary()
        }
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute(
                "SELECT sweep_id, diffusion_coeff FROM diffusion_summary"
            ).fetchall()
        finally:
            conn.close()
        actual = {row["sweep_id"]: float(row["diffusion_coeff"]) for row in rows}
        assert actual == expected

    def test_rss_values(self) -> None:
        """RSS must be sum of squared MSD fit residuals."""
        expected = {row["sweep_id"]: row["rss"] for row in diffusion_ref.expected_summary()}
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute("SELECT sweep_id, rss FROM diffusion_summary").fetchall()
        finally:
            conn.close()
        actual = {row["sweep_id"]: float(row["rss"]) for row in rows}
        assert actual == expected

    def test_zeta_uses_custom_fit_window(self) -> None:
        """sweep-zeta must fit lags 3-5, not the default 2-5 window."""
        conn = diffusion_ref.connect()
        try:
            row = conn.execute(
                "SELECT diffusion_coeff FROM diffusion_summary WHERE sweep_id = 'sweep-zeta'"
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert float(row["diffusion_coeff"]) == 0.6

    def test_epsilon_has_nonzero_rss(self) -> None:
        """Noisy sweep-epsilon must produce a positive RSS."""
        conn = diffusion_ref.connect()
        try:
            row = conn.execute(
                "SELECT rss FROM diffusion_summary WHERE sweep_id = 'sweep-epsilon'"
            ).fetchone()
        finally:
            conn.close()
        assert row is not None
        assert float(row["rss"]) > 0

    def test_summary_kernel_revision_matches_import(self) -> None:
        """Summary rows must carry resolved kernel revisions."""
        expected = {
            row["sweep_id"]: row["kernel_revision"] for row in diffusion_ref.expected_summary()
        }
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute(
                "SELECT sweep_id, kernel_revision FROM diffusion_summary"
            ).fetchall()
        finally:
            conn.close()
        actual = {row["sweep_id"]: row["kernel_revision"] for row in rows}
        assert actual == expected
