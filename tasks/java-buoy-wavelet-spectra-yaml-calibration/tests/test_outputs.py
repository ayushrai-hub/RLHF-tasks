"""Behavioral tests for Java buoy wavelet spectra pipeline."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from reference_spectra import reference_run

APP = Path("/app")
JAR = APP / "target" / "buoy-spectra-jar-with-dependencies.jar"
RUNNER = APP / "scripts" / "run-spectra-pipeline.sh"
BUNDLE_MANIFEST = APP / "fixtures" / "manifests" / "storm-alpha.json"
BETA_MANIFEST = APP / "fixtures" / "manifests" / "storm-beta.json"
HIDDEN = Path("/opt/verifier-fixtures/buoy-spectra-probes")
DOSSIER = APP / "docs" / "coastal-operations-dossier.md"

TOL = 1e-3


def run_pipeline(manifest: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(RUNNER), "--manifest", str(manifest), "--output", str(report)],
        capture_output=True,
        text=True,
        cwd=str(APP),
    )


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_report_close(got: dict, ref: dict) -> None:
    assert got["run_id"] == ref["run_id"]
    assert got["samples_used"] == ref["samples_used"]
    for key in ("significant_wave_height_m", "peak_period_s", "coi_masked_ratio", "drift_correction_pa"):
        assert abs(got[key] - ref[key]) <= TOL, f"{key}: got={got[key]} ref={ref[key]}"


def test_jar_and_runner_exist():
    """Pipeline jar and bash runner must be installed under /app."""
    assert JAR.is_file()
    assert RUNNER.is_file()


def test_bundled_storm_alpha_report(tmp_path: Path):
    """Bundled storm-alpha manifest produces schema-valid report matching reference."""
    report = tmp_path / "alpha.json"
    ref = reference_run(BUNDLE_MANIFEST)
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0, proc.stderr
    assert_report_close(load_report(report), ref)


def test_bundled_storm_beta_report(tmp_path: Path):
    """storm-beta manifest must ignore manifest sample_rate_hz hint (profile wins)."""
    report = tmp_path / "beta.json"
    ref = reference_run(BETA_MANIFEST)
    proc = run_pipeline(BETA_MANIFEST, report)
    assert proc.returncode == 0, proc.stderr
    assert_report_close(load_report(report), ref)


def test_hidden_probe_shift_report(tmp_path: Path):
    """Hidden probe under /opt/verifier-fixtures/buoy-spectra-probes replays correctly."""
    manifest = HIDDEN / "manifests" / "probe-shift.json"
    report = tmp_path / "hidden.json"
    ref = reference_run(manifest, HIDDEN)
    proc = run_pipeline(manifest, report)
    assert proc.returncode == 0, proc.stderr
    assert_report_close(load_report(report), ref)


def test_hidden_probe_coarse_report(tmp_path: Path):
    """Second /opt/verifier-fixtures probe-coarse manifest must match independent reference."""
    manifest = Path("/opt/verifier-fixtures/buoy-spectra-probes/manifests/probe-coarse.json")
    report = tmp_path / "coarse.json"
    ref = reference_run(manifest, HIDDEN)
    proc = run_pipeline(manifest, report)
    assert proc.returncode == 0, proc.stderr
    assert_report_close(load_report(report), ref)


def test_staging_snapshot_export_after_manifest_ingest(tmp_path: Path):
    """Ingest probe manifest, write staging snapshot export JSON, and match reference export."""
    staging_snapshot = tmp_path / "staging-export-snapshot.json"
    manifest = Path("/opt/verifier-fixtures/buoy-spectra-probes/manifests/probe-coarse.json")
    ref = reference_run(manifest, HIDDEN)
    proc = run_pipeline(manifest, staging_snapshot)
    assert proc.returncode == 0, proc.stderr
    assert_report_close(load_report(staging_snapshot), ref)


def test_fetch_manifest_curl():
    """fetch-manifest.sh uses curl against local file:// fixture catalog offline."""
    url = "file:///app/fixtures/manifests/storm-alpha.json"
    proc = subprocess.run(
        ["/app/scripts/fetch-manifest.sh", url],
        capture_output=True,
        text=True,
        cwd=str(APP),
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["run_id"] == "storm-alpha"


def test_coastal_dossier_long_context():
    """Long-form dossier cited in instruction must exist and exceed long-context size gate."""
    assert DOSSIER.is_file()
    text = DOSSIER.read_text(encoding="utf-8")
    assert "FINAL CALIBRATION MEMO" in text
    assert len(text) > 200_000


def test_report_schema_fields(tmp_path: Path):
    """Report JSON exposes all fields from /app/docs/report-schema.md."""
    report = tmp_path / "schema.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    data = load_report(report)
    for key in (
        "run_id",
        "significant_wave_height_m",
        "peak_period_s",
        "coi_masked_ratio",
        "samples_used",
        "drift_correction_pa",
    ):
        assert key in data


def test_reference_independent_bundled():
    """Independent reference_run agrees with bundled storm-alpha expectations."""
    ref = reference_run(BUNDLE_MANIFEST)
    assert ref["samples_used"] > 100
    assert ref["significant_wave_height_m"] > 0


def test_invalid_manifest_fails(tmp_path: Path):
    """Pipeline exits non-zero when manifest path is missing."""
    proc = run_pipeline(APP / "fixtures/manifests/missing.json", tmp_path / "x.json")
    assert proc.returncode != 0


def test_toml_drift_precedence_reflected(tmp_path: Path):
    """Merged TOML drift rate (0.18) must drive report drift_correction_pa not YAML 0.12."""
    report = tmp_path / "drift.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    ref = reference_run(BUNDLE_MANIFEST)
    got = load_report(report)
    assert abs(got["drift_correction_pa"] - ref["drift_correction_pa"]) <= TOL


def test_decoy_not_compiled():
    """Decoy shortcut under /app/decoy must not ship inside the production jar."""
    proc = subprocess.run(
        ["jar", "tf", str(JAR)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "SpectraShortcut" not in proc.stdout


def test_coi_ratio_within_bounds(tmp_path: Path):
    """coi_masked_ratio must stay within [0,1] for bundled run."""
    report = tmp_path / "coi.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    ratio = load_report(report)["coi_masked_ratio"]
    assert 0.0 <= ratio <= 1.0


def test_run_id_matches_manifest(tmp_path: Path):
    """report.run_id must equal manifest run_id field."""
    report = tmp_path / "rid.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    assert load_report(report)["run_id"] == "storm-alpha"


def test_significant_wave_height_positive(tmp_path: Path):
    """significant_wave_height_m must be positive for storm-alpha."""
    report = tmp_path / "hs.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    assert load_report(report)["significant_wave_height_m"] > 0


def test_peak_period_positive(tmp_path: Path):
    """peak_period_s must be positive for storm-alpha."""
    report = tmp_path / "tp.json"
    proc = run_pipeline(BUNDLE_MANIFEST, report)
    assert proc.returncode == 0
    assert load_report(report)["peak_period_s"] > 0


def test_idempotent_pipeline_runs(tmp_path: Path):
    """Two consecutive runs produce identical report JSON."""
    r1 = tmp_path / "a.json"
    r2 = tmp_path / "b.json"
    assert run_pipeline(BUNDLE_MANIFEST, r1).returncode == 0
    assert run_pipeline(BUNDLE_MANIFEST, r2).returncode == 0
    assert load_report(r1) == load_report(r2)


def test_hidden_differs_from_bundled(tmp_path: Path):
    """Hidden probe-shift report must differ from bundled storm-alpha."""
    bundled = tmp_path / "bundled.json"
    hidden = tmp_path / "hidden.json"
    assert run_pipeline(BUNDLE_MANIFEST, bundled).returncode == 0
    assert run_pipeline(HIDDEN / "manifests" / "probe-shift.json", hidden).returncode == 0
    b = load_report(bundled)
    h = load_report(hidden)
    assert b["run_id"] != h["run_id"]
    assert b["significant_wave_height_m"] != h["significant_wave_height_m"]


def test_profile_and_overlay_files_exist():
    """Processing profile YAML and TOML overlay paths must exist under /app."""
    assert (APP / "profiles" / "storm-processing.yaml").is_file()
    assert (APP / "profiles" / "site-calibration.toml").is_file()


def test_contract_docs_exist():
    """Contract docs referenced in instruction must exist under /app/docs/."""
    for name in ("processing-contract.md", "report-schema.md", "config-precedence.md"):
        assert (APP / "docs" / name).is_file()


def test_httpie_installed():
    """HTTPie ships in the image for manifest fetch workflows."""
    proc = subprocess.run(["http", "--version"], capture_output=True, text=True)
    assert proc.returncode == 0


def test_manifest_series_fixture_exists():
    """Bundled CSV series for storm-alpha must exist on disk."""
    assert (APP / "fixtures" / "series" / "storm-alpha.csv").is_file()
