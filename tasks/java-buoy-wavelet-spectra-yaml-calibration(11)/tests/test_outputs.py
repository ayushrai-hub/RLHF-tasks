"""Behavioral tests for Java buoy wavelet spectra pipeline."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from reference_spectra import (
    STAGING,
    COMMIT,
    commit_manifest,
    ingest_snapshot,
    reference_run,
)

APP = Path("/app")
JAR = APP / "target" / "buoy-spectra-jar-with-dependencies.jar"
RUNNER = APP / "scripts" / "run-spectra-pipeline.sh"
BUNDLE_MANIFEST = APP / "fixtures" / "manifests" / "storm-alpha.json"
BETA_MANIFEST = APP / "fixtures" / "manifests" / "storm-beta.json"
HIDDEN = Path("/opt/verifier-fixtures/buoy-spectra-probes")
DOSSIER = APP / "docs" / "coastal-operations-dossier.md"
STATE_DIR = APP / "state"

TOL = 1e-3


def run_java(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["java", "-jar", str(JAR), *args],
        capture_output=True,
        text=True,
        cwd=str(APP),
    )


def run_ingest(manifest: Path) -> subprocess.CompletedProcess[str]:
    return run_java("ingest", "--manifest", str(manifest))


def run_export(manifest: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return run_java("export", "--manifest", str(manifest), "--output", str(report))


def run_pipeline(manifest: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(RUNNER), "--manifest", str(manifest), "--output", str(report)],
        capture_output=True,
        text=True,
        cwd=str(APP),
    )


def clear_staging_state() -> None:
    for path in (STAGING, COMMIT):
        if path.is_file():
            path.unlink()


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


def test_hidden_probe_tree_not_under_app():
    """Verifier-only probe fixtures must not remain readable under /app."""
    assert not (APP / "verifier-fixtures").exists()
    assert HIDDEN.is_dir()
    assert (HIDDEN / "manifests" / "probe-shift.json").is_file()


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
    """Split ingest then export on hidden probe manifest must match reference report."""
    manifest = HIDDEN / "manifests" / "probe-coarse.json"
    report = tmp_path / "split-export.json"
    ref = reference_run(manifest, HIDDEN)
    clear_staging_state()
    ingest = run_ingest(manifest)
    assert ingest.returncode == 0, ingest.stderr
    assert STAGING.is_file()
    assert COMMIT.is_file()
    export = run_export(manifest, report)
    assert export.returncode == 0, export.stderr
    assert_report_close(load_report(report), ref)


def test_ingest_writes_staging_and_commit_bind():
    """Ingest must persist spectra-ingest-snapshot.json and spectra-commit-bind.json under /app/state."""
    clear_staging_state()
    ref_snap = ingest_snapshot(BUNDLE_MANIFEST)
    ref_commit = commit_manifest(ref_snap)
    proc = run_ingest(BUNDLE_MANIFEST)
    assert proc.returncode == 0, proc.stderr
    assert STATE_DIR.is_dir()
    assert STAGING.is_file()
    assert COMMIT.is_file()
    got_snap = json.loads(STAGING.read_text(encoding="utf-8"))
    got_commit = json.loads(COMMIT.read_text(encoding="utf-8"))
    assert got_snap["run_id"] == ref_snap["run_id"]
    assert got_snap["profile_fingerprint"] == ref_snap["profile_fingerprint"]
    assert got_snap["samples_used"] == ref_snap["samples_used"]
    assert len(got_snap["filled_pressures"]) == len(ref_snap["filled_pressures"])
    for i, (g, r) in enumerate(zip(got_snap["filled_pressures"], ref_snap["filled_pressures"])):
        assert abs(g - r) <= TOL, f"filled_pressures[{i}]"
    assert got_commit == ref_commit


def test_export_without_prior_ingest_fails(tmp_path: Path):
    """Export alone must fail when staging artifacts are absent."""
    clear_staging_state()
    proc = run_export(BUNDLE_MANIFEST, tmp_path / "orphan.json")
    assert proc.returncode != 0


def test_tampered_spectral_bind_rejected_on_export(tmp_path: Path):
    """Export must reject commit manifest when spectral_bind no longer matches staging."""
    clear_staging_state()
    assert run_ingest(BUNDLE_MANIFEST).returncode == 0
    commit = json.loads(COMMIT.read_text(encoding="utf-8"))
    commit["spectral_bind"] = "0" * 64
    COMMIT.write_text(json.dumps(commit), encoding="utf-8")
    proc = run_export(BUNDLE_MANIFEST, tmp_path / "tampered.json")
    assert proc.returncode != 0


def test_export_uses_staging_not_raw_csv(tmp_path: Path):
    """Export must spectral-analyze staged pressures even if the CSV changes after ingest."""
    csv_path = APP / "fixtures" / "series" / "storm-alpha.csv"
    backup = tmp_path / "storm-alpha.csv.bak"
    shutil.copy(csv_path, backup)
    report = tmp_path / "csv-trap.json"
    ref = reference_run(BUNDLE_MANIFEST)
    try:
        clear_staging_state()
        assert run_ingest(BUNDLE_MANIFEST).returncode == 0
        lines = csv_path.read_text(encoding="utf-8").splitlines()
        parts = lines[1].split(",")
        parts[1] = str(float(parts[1]) + 5000.0)
        lines[1] = ",".join(parts)
        csv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        proc = run_export(BUNDLE_MANIFEST, report)
        assert proc.returncode == 0, proc.stderr
        assert_report_close(load_report(report), ref)
    finally:
        shutil.copy(backup, csv_path)


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
    for name in (
        "processing-contract.md",
        "report-schema.md",
        "config-precedence.md",
        "staging-contract.md",
        "commit-manifest.md",
        "shell-runbook.md",
    ):
        assert (APP / "docs" / name).is_file()


def test_httpie_installed():
    """HTTPie ships in the image for manifest fetch workflows."""
    proc = subprocess.run(["http", "--version"], capture_output=True, text=True)
    assert proc.returncode == 0


def test_manifest_series_fixture_exists():
    """Bundled CSV series for storm-alpha must exist on disk."""
    assert (APP / "fixtures" / "series" / "storm-alpha.csv").is_file()
