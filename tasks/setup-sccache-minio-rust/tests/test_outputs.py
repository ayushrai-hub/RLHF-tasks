"""Verifier tests for the sccache + MinIO Rust workspace task."""

import json
import re
import subprocess
from pathlib import Path

REPORT_PATH = Path("/app/reports/sccache-benchmark.json")
REPLAY_STATS_PATH = Path("/app/reports/sccache-replay-stats.txt")
APP_ROOT = Path("/app")
MINIO_DATA_ROOT = Path("/var/minio/data")
_minio_cfg = APP_ROOT / "config" / "backend-cache.toml"
if _minio_cfg.is_file():
    for line in _minio_cfg.read_text().splitlines():
        line = line.strip()
        if line.startswith("data_dir"):
            MINIO_DATA_ROOT = Path(line.split("=", 1)[1].strip().strip('"'))
            break
CARGO_CONFIG = APP_ROOT / ".cargo" / "config.toml"
REQUIRED_TOP_LEVEL = (
    "cold_seconds",
    "warm_seconds",
    "post_clean_seconds",
)
REQUIRED_PHASES = ("cold", "warm", "post_clean")
PHASE_FIELDS = ("hits", "misses", "compilations")


def _load_report() -> dict:
    assert REPORT_PATH.is_file(), f"Missing benchmark report at {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text())


def _parse_sccache_stat(stats_text: str, label: str) -> int:
    """Return the trailing integer from an exact sccache --show-stats counter line."""
    patterns = {
        "cache hits": re.compile(r"^Cache hits\s+(\d+)\s*$"),
        "cache misses": re.compile(r"^Cache misses\s+(\d+)\s*$"),
        "compile requests executed": re.compile(
            r"^Compile requests executed\s+(\d+)\s*$"
        ),
        "non-cacheable compilations": re.compile(
            r"^Non-cacheable compilations\s+(\d+)\s*$"
        ),
    }
    pattern = patterns.get(label.lower())
    assert pattern is not None, f"Unsupported sccache stat label: {label!r}"
    for line in stats_text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return int(match.group(1))
    return 0


def _parse_sccache_float(stats_text: str, label: str) -> float:
    """Return a float metric from an exact sccache --show-stats line."""
    patterns = {
        "average cache read hit": re.compile(
            r"^Average cache read hit\s+(\d+(?:\.\d+)?)\s+s\s*$"
        ),
    }
    pattern = patterns.get(label.lower())
    assert pattern is not None, f"Unsupported sccache float stat label: {label!r}"
    for line in stats_text.splitlines():
        match = pattern.match(line.strip())
        if match:
            return float(match.group(1))
    return 0.0


def _validate_authentic_sccache_stats(stats_text: str) -> None:
    """Reject trimmed or fabricated stats that omit real sccache --show-stats sections."""
    required_markers = (
        "Compile requests",
        "Compile requests executed",
        "Cache hits rate",
        "Cache read errors",
        "Compilations",
        "Non-cacheable reasons:",
        "Cache location",
        "Version (client)",
    )
    missing = [marker for marker in required_markers if marker not in stats_text]
    assert not missing, (
        "Replay stats must be raw sccache --show-stats output; "
        f"missing sections: {missing}\ncontents:\n{stats_text}"
    )


def _configured_bucket() -> str:
    minio_cfg = APP_ROOT / "config" / "backend-cache.toml"
    if not minio_cfg.is_file():
        return "rust-sccache"
    for line in minio_cfg.read_text().splitlines():
        line = line.strip()
        if line.startswith("bucket"):
            return line.split("=", 1)[1].strip().strip('"')
    return "rust-sccache"


def _minio_cache_files() -> list[Path]:
    """Collect non-metadata object files written by MinIO for the remote cache."""
    if not MINIO_DATA_ROOT.is_dir():
        return []
    bucket_root = MINIO_DATA_ROOT / _configured_bucket()
    search_root = bucket_root if bucket_root.is_dir() else MINIO_DATA_ROOT
    return [
        path
        for path in search_root.rglob("*")
        if path.is_file() and ".minio.sys" not in path.parts
    ]


def _replay_post_clean_stats() -> str:
    """Read replay stats captured during the agent session after the benchmark report."""
    assert REPLAY_STATS_PATH.is_file(), (
        "Missing replay stats at /app/reports/sccache-replay-stats.txt; "
        "capture a post-clean verification build in the same session as the benchmark"
    )
    stats_text = REPLAY_STATS_PATH.read_text()
    assert "Cache hits" in stats_text, (
        "Replay stats output is missing sccache counters\n"
        f"contents:\n{stats_text}"
    )
    assert "Cache location" in stats_text and "s3" in stats_text.lower(), (
        "Replay stats must come from an sccache daemon using the configured S3 backend\n"
        f"contents:\n{stats_text}"
    )
    return stats_text


def test_report_file_exists():
    """Verify the benchmark report was written to the path named in instruction.md."""
    assert REPORT_PATH.is_file(), f"Expected report at {REPORT_PATH}"


def test_report_contains_required_schema():
    """Verify the JSON report includes all top-level and per-phase fields from the prompt."""
    report = _load_report()

    allowed_top_level = set(REQUIRED_TOP_LEVEL) | set(REQUIRED_PHASES)
    extra = set(report.keys()) - allowed_top_level
    assert not extra, f"Report has unexpected top-level keys: {sorted(extra)}"
    for forbidden in ("phases", "sccache", "benchmark"):
        assert forbidden not in report, (
            f"Phase data must not be nested under {forbidden!r}"
        )

    for key in REQUIRED_TOP_LEVEL:
        assert key in report, f"Report missing top-level field {key!r}"
        assert isinstance(report[key], (int, float)), f"{key} must be numeric"
        assert report[key] >= 0, f"{key} must be non-negative"

    for phase in REQUIRED_PHASES:
        assert phase in report, f"Report missing phase block {phase!r}"
        block = report[phase]
        assert isinstance(block, dict), f"{phase} must be an object"
        for field in PHASE_FIELDS:
            assert field in block, f"{phase} missing {field!r}"
            assert isinstance(block[field], int), f"{phase}.{field} must be an integer"
            assert block[field] >= 0, f"{phase}.{field} must be non-negative"


def test_warm_build_is_faster_than_cold():
    """Verify cold timing reflects a real compile and warm is substantially faster."""
    report = _load_report()
    cold = float(report["cold_seconds"])
    warm = float(report["warm_seconds"])

    assert cold >= 5.0, (
        "cold_seconds should reflect a multi-crate workspace compile of several seconds"
    )
    assert warm >= 0.001, (
        "warm_seconds must use fractional timing; sub-second warm builds must not truncate to 0"
    )
    assert warm < cold * 0.5, (
        "Warm build should be substantially faster than cold, not marginally faster"
    )


def test_post_clean_timing_reflects_target_rebuild():
    """Verify post-clean timing reflects a real rebuild after target/ was removed."""
    report = _load_report()
    warm = float(report["warm_seconds"])
    post_clean = float(report["post_clean_seconds"])

    assert post_clean >= 1.0, (
        "post_clean_seconds should reflect a rebuild after deleting target/ trees"
    )
    assert post_clean > warm, (
        "Post-clean rebuild should take longer than the warm incremental rebuild"
    )


def test_cold_build_populated_the_cache():
    """Verify the first build populated the remote cache with cacheable crate artifacts."""
    report = _load_report()
    cold = report["cold"]
    assert cold["hits"] == 0, "Cold phase should not record prior cache hits"
    assert cold["misses"] > 0, (
        "Cold phase should record cache misses for cacheable crate compilations"
    )


def test_warm_build_avoids_new_compilation_work():
    """Verify the warm rebuild with unchanged sources did not record new cache misses."""
    report = _load_report()
    warm = report["warm"]
    assert warm["misses"] == 0, "Warm phase should not record new cache misses"
    assert warm["compilations"] == 0, (
        "Warm phase should not trigger non-cacheable compilations"
    )


def test_post_clean_rebuild_relies_on_cache():
    """Verify deleting target/ still yields cache hits dominating over fresh compilations."""
    report = _load_report()
    post = report["post_clean"]
    assert post["hits"] > 0, "Post-clean phase should record cache hits"
    assert post["hits"] > post["compilations"], (
        "Post-clean hits should dominate over fresh compilations"
    )
    assert post["hits"] >= report["cold"]["misses"], (
        "Post-clean cache hits should reflect artifacts seeded during the cold build"
    )


def test_remote_cache_store_contains_objects():
    """Verify compile artifacts were persisted to the configured MinIO bucket."""
    report = _load_report()
    bucket = _configured_bucket()
    bucket_root = MINIO_DATA_ROOT / bucket
    assert bucket_root.is_dir(), (
        f"Expected MinIO bucket directory for {bucket!r} under {MINIO_DATA_ROOT}"
    )
    cache_files = _minio_cache_files()
    assert len(cache_files) > 0, (
        f"Expected cached objects under {bucket_root} after a successful benchmark"
    )
    assert len(cache_files) >= report["cold"]["misses"], (
        "Remote cache should contain at least as many objects as cold cache misses"
    )


def test_post_clean_replay_confirms_remote_cache():
    """Verify post-clean replay stats prove an independent rebuild hit the remote cache."""
    report = _load_report()
    stats_text = _replay_post_clean_stats()
    _validate_authentic_sccache_stats(stats_text)

    live_hits = _parse_sccache_stat(stats_text, "cache hits")
    live_misses = _parse_sccache_stat(stats_text, "cache misses")
    executed = _parse_sccache_stat(stats_text, "compile requests executed")
    read_hit_seconds = _parse_sccache_float(stats_text, "average cache read hit")
    cold_misses = report["cold"]["misses"]
    reported_post_hits = report["post_clean"]["hits"]

    assert live_hits > 0, (
        "Replay build should record cache hits from the remote cache\n"
        f"stats:\n{stats_text}"
    )
    assert live_misses == 0, (
        "Verification replay should read the remote cache without new misses\n"
        f"stats:\n{stats_text}"
    )
    assert executed >= cold_misses, (
        f"Verification replay executed {executed} compiles; "
        f"expected at least {cold_misses} from the cold fill"
    )
    assert read_hit_seconds > 0.0, (
        "Verification replay should show non-zero average cache read hit time\n"
        f"stats:\n{stats_text}"
    )
    assert live_hits >= cold_misses, (
        f"Replay cache hits ({live_hits}) should reflect cold misses ({cold_misses})"
    )
    assert live_hits >= reported_post_hits, (
        f"Replay cache hits ({live_hits}) should corroborate reported post_clean hits "
        f"({reported_post_hits})"
    )


def test_workspace_binary_exists():
    """Verify the meridian-cli binary was produced by the workspace build."""
    binary = APP_ROOT / "target" / "debug" / "meridian-cli"
    assert binary.is_file(), f"Expected workspace binary at {binary}"


def test_crate_sources_were_not_modified():
    """Verify crate sources under /app/crates remain identical to the seeded workspace."""
    result = subprocess.run(
        ["git", "-C", str(APP_ROOT), "diff", "--quiet", "crates/"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Crate sources under /app/crates were modified\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_report_does_not_use_legacy_layout():
    """Verify the report avoids legacy nested layouts and field names from old samples."""
    report = _load_report()
    raw = REPORT_PATH.read_text()
    for legacy in ("cache_hits", "cache_misses", "duration_sec", '"benchmark"'):
        assert legacy not in raw, f"Report uses legacy field or layout: {legacy!r}"
    assert "phases" not in report, "Phase data must be top-level, not nested under phases"


def test_sccache_is_wired_into_cargo():
    """Verify Cargo is configured to route compilation through sccache."""
    assert CARGO_CONFIG.is_file(), f"Missing Cargo config at {CARGO_CONFIG}"
    config = CARGO_CONFIG.read_text()
    assert "rustc-wrapper" in config, (
        "Cargo config must set rustc-wrapper under [build]"
    )
    assert "sccache" in config, "Cargo config must reference sccache"
