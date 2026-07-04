"""Milestone 1 verifier tests for sweep import migration."""

from __future__ import annotations

import diffusion_ref


class TestMilestone1:
    """Import migration checks."""

    def test_all_sweeps_imported(self) -> None:
        """Every fixture sweep must exist in sweeps table."""
        expected = {row["sweep_id"] for row in diffusion_ref.expected_sweeps()}
        conn = diffusion_ref.connect()
        try:
            actual = {row["sweep_id"] for row in conn.execute("SELECT sweep_id FROM sweeps")}
        finally:
            conn.close()
        assert actual == expected

    def test_kernel_revision_resolves_replace(self) -> None:
        """kernel_revision must follow go.mod replace targets."""
        expected = {row["sweep_id"]: row["kernel_revision"] for row in diffusion_ref.expected_sweeps()}
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute("SELECT sweep_id, kernel_revision FROM sweeps").fetchall()
        finally:
            conn.close()
        actual = {row["sweep_id"]: row["kernel_revision"] for row in rows}
        assert actual == expected

    def test_chained_replace_resolves_final_target(self) -> None:
        """rd-sim sweeps must resolve through rd-patch to rd-fast v1.3.2."""
        expected = "example.com/rd-kernel@v1.3.2"
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute(
                """
                SELECT kernel_revision FROM sweeps
                WHERE sweep_id IN ('sweep-alpha', 'sweep-gamma', 'sweep-zeta')
                """
            ).fetchall()
        finally:
            conn.close()
        assert rows
        assert all(row["kernel_revision"] == expected for row in rows)

    def test_kernel_revision_not_wrapper_module(self) -> None:
        """kernel_revision must not equal wrapper module paths from fixtures."""
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute("SELECT sweep_id, kernel_revision FROM sweeps").fetchall()
        finally:
            conn.close()
        for row in rows:
            assert not row["kernel_revision"].startswith("example.com/rd-sim@")
            assert not row["kernel_revision"].startswith("example.com/rd-lite@")

    def test_msd_points_match_fixtures(self) -> None:
        """MSD samples must match nested fixture series."""
        conn = diffusion_ref.connect()
        try:
            for sweep in diffusion_ref.expected_sweeps():
                expected_points = diffusion_ref.expected_msd_points(sweep["sweep_id"])
                rows = conn.execute(
                    "SELECT lag_step, msd FROM msd_points WHERE sweep_id = ? ORDER BY lag_step",
                    (sweep["sweep_id"],),
                ).fetchall()
                actual_points = [(int(row["lag_step"]), float(row["msd"])) for row in rows]
                assert actual_points == expected_points
        finally:
            conn.close()

    def test_sweep_params_persisted(self) -> None:
        """dt and dimension must match fixture params."""
        expected = {
            row["sweep_id"]: (row["dt"], row["dimension"]) for row in diffusion_ref.expected_sweeps()
        }
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute("SELECT sweep_id, dt, dimension FROM sweeps").fetchall()
        finally:
            conn.close()
        actual = {row["sweep_id"]: (float(row["dt"]), int(row["dimension"])) for row in rows}
        assert actual == expected

    def test_fit_lag_window_persisted(self) -> None:
        """Per-sweep fit lag bounds must be stored on sweeps rows."""
        expected = {
            row["sweep_id"]: (row["fit_lag_min"], row["fit_lag_max"])
            for row in diffusion_ref.expected_sweeps()
        }
        conn = diffusion_ref.connect()
        try:
            rows = conn.execute(
                "SELECT sweep_id, fit_lag_min, fit_lag_max FROM sweeps"
            ).fetchall()
        finally:
            conn.close()
        actual = {
            row["sweep_id"]: (int(row["fit_lag_min"]), int(row["fit_lag_max"])) for row in rows
        }
        assert actual == expected

    def test_invalid_fixture_skipped(self) -> None:
        """Fixtures without meta.run.id must not be imported."""
        conn = diffusion_ref.connect()
        try:
            count = conn.execute(
                "SELECT count(*) FROM sweeps WHERE sweep_id LIKE 'draft%'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert count == 0
