"""Tests for the file-deduplicator Rust binary."""

import json
import os
import subprocess
import tempfile


REPORT_PATH = "/app/output/report.json"
BINARY_PATH = "/app/target/release/file-deduplicator"
SAMPLE_DATA = "/app/data/sample_files"


def _run_deduplicator(args, check=True):
    """Run the deduplicator binary with given args."""
    cmd = [BINARY_PATH] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"stderr: {result.stderr}")
        print(f"stdout: {result.stdout}")
    return result


def _load_report(path=REPORT_PATH):
    """Load the JSON report."""
    with open(path) as f:
        return json.load(f)


def _generate_test_data(dir_path, with_hidden=False, with_empty=False):
    """Create deterministic test data."""
    os.makedirs(dir_path, exist_ok=True)

    files = {}
    files["unique_a.txt"] = "alpha_content"
    files["unique_b.txt"] = "beta_content"
    files["dup_x_1.txt"] = "duplicate_value_x"
    files["dup_x_2.txt"] = "duplicate_value_x"
    files["dup_y_1.txt"] = "duplicate_value_y"
    files["dup_y_2.txt"] = "duplicate_value_y"

    for name, content in files.items():
        with open(os.path.join(dir_path, name), "w") as f:
            f.write(content)

    if with_hidden:
        with open(os.path.join(dir_path, ".secret.txt"), "w") as f:
            f.write("hidden_content")

    if with_empty:
        open(os.path.join(dir_path, "empty.txt"), "w").close()

    return len(files), sum(len(c) for c in files.values())


class TestBinaryExists:
    """Tests that the binary and output infrastructure work."""

    def test_binary_compiles(self):
        """Verify the deduplicator binary exists and is executable."""
        assert os.path.exists(BINARY_PATH), f"Binary not found at {BINARY_PATH}"
        assert os.access(BINARY_PATH, os.X_OK), "Binary is not executable"

    def test_report_exists_after_run(self):
        """Verify running the tool produces a report file."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        assert os.path.exists(REPORT_PATH), "Report file was not created"
        report = _load_report()
        assert "scan" in report
        assert "dedup" in report


class TestScanCorrectness:
    """Tests for correct directory scanning behavior."""

    def test_total_size_computed_correctly(self):
        """Verify scan.total_size equals the arithmetic sum of all file sizes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_count, expected_size = _generate_test_data(tmpdir)
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])
            report = _load_report(out_path)
            assert report["scan"]["total_size"] == expected_size, (
                f"total_size {report['scan']['total_size']} != expected {expected_size}"
            )

    def test_total_files_count(self):
        """Verify scan.total_files matches discovered file count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_count, _ = _generate_test_data(tmpdir)
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])
            report = _load_report(out_path)
            assert report["scan"]["total_files"] == file_count

    def test_min_size_inclusive(self):
        """Verify that files with size exactly equal to min_size are included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with exactly 5 bytes
            with open(os.path.join(tmpdir, "five.txt"), "w") as f:
                f.write("12345")
            # Create a file with 4 bytes (should be excluded with min_size=5)
            with open(os.path.join(tmpdir, "four.txt"), "w") as f:
                f.write("1234")
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator([
                "--paths", tmpdir, "--output", out_path, "--dry-run",
                "--min-size", "5"
            ])
            report = _load_report(out_path)
            # five.txt (5 bytes) should be included, four.txt (4 bytes) excluded
            assert report["scan"]["total_files"] == 1, (
                f"Expected 1 file (5 bytes), got {report['scan']['total_files']}"
            )
            assert report["scan"]["total_size"] == 5

    def test_recursive_scanning_includes_subdirectory_files(self):
        """Verify that files in subdirectories are discovered and counted."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in root
            with open(os.path.join(tmpdir, "root_a.txt"), "w") as f:
                f.write("root_content_a")
            with open(os.path.join(tmpdir, "root_b.txt"), "w") as f:
                f.write("root_content_b")

            # Create files in a subdirectory
            subdir = os.path.join(tmpdir, "nested")
            os.makedirs(subdir)
            with open(os.path.join(subdir, "sub_a.txt"), "w") as f:
                f.write("sub_content_a")
            with open(os.path.join(subdir, "sub_b.txt"), "w") as f:
                f.write("sub_content_b")

            # Create files in a deeper subdirectory
            deep = os.path.join(subdir, "deep")
            os.makedirs(deep)
            with open(os.path.join(deep, "deep_a.txt"), "w") as f:
                f.write("deep_content_a")

            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])
            report = _load_report(out_path)

            # Should find all 5 files across root, nested/, and nested/deep/
            assert report["scan"]["total_files"] == 5, (
                f"Expected 5 files (recursive scan), got {report['scan']['total_files']}"
            )
            expected_size = len("root_content_a") + len("root_content_b") + \
                len("sub_content_a") + len("sub_content_b") + len("deep_content_a")
            assert report["scan"]["total_size"] == expected_size, (
                f"Expected total_size {expected_size}, got {report['scan']['total_size']}"
            )


class TestDedupCorrectness:
    """Tests for correct deduplication logic."""

    def test_duplicate_files_count_excludes_originals(self):
        """Verify duplicate_files counts only redundant copies, not kept files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _generate_test_data(tmpdir)
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"],
                              check=False)
            report = _load_report(out_path)

            total_in_groups = sum(len(g["files"]) for g in report["duplicate_groups"])
            kept_count = report["dedup"]["duplicate_groups"]
            expected_dup_files = total_in_groups - kept_count

            assert report["dedup"]["duplicate_files"] == expected_dup_files, (
                f"duplicate_files {report['dedup']['duplicate_files']} != "
                f"expected {expected_dup_files}"
            )

    def test_dry_run_does_not_delete_files(self):
        """Verify --dry-run does not delete source files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _generate_test_data(tmpdir)
            files_before = set()
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    files_before.add(os.path.join(root, f))

            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])

            files_after = set()
            for root, dirs, files in os.walk(tmpdir):
                for f in files:
                    if f != "report.json":
                        files_after.add(os.path.join(root, f))

            assert files_before == files_after

    def test_dry_run_flag_in_report(self):
        """Verify dedup.dry_run is true when --dry-run is passed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _generate_test_data(tmpdir)
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])
            report = _load_report(out_path)
            assert report["dedup"]["dry_run"] is True

    def test_dedup_actions_taken_matches_total_removed(self):
        """Verify actions_taken and total_removed are consistent with groups."""
        with tempfile.TemporaryDirectory() as tmpdir:
            _generate_test_data(tmpdir)
            out_path = os.path.join(tmpdir, "report.json")
            _run_deduplicator(["--paths", tmpdir, "--output", out_path, "--dry-run"])
            report = _load_report(out_path)

            dup_groups = report["duplicate_groups"]
            expected_removed = sum(len(g["files"]) - 1 for g in dup_groups)
            expected_actions = len(dup_groups)
            assert report["dedup"]["total_removed"] == expected_removed
            assert report["dedup"]["actions_taken"] == expected_actions


class TestConfigOverrides:
    """Tests for correct config override merging."""

    def test_report_contains_all_required_keys(self):
        """Verify all required top-level keys exist in the report."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        required = {"scan", "hashing", "duplicate_groups", "dedup", "config", "errors"}
        missing = required - set(report.keys())
        assert not missing, f"Missing keys: {missing}"

    def test_selective_merge_retains_untouched_section(self):
        """Verify config sections absent from overrides keep base values.

        The [report] section is not in overrides.toml, so report_format
        must remain 'detailed' from the base config.
        """
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert report["config"]["report_format"] == "detailed", (
            f"Expected 'detailed', got '{report['config']['report_format']}'"
        )

    def test_config_has_buffer_size_field(self):
        """Verify config includes buffer_size from overrides."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert "buffer_size" in report["config"]
        assert report["config"]["buffer_size"] == 65536, (
            f"Expected 65536 from overrides, got {report['config']['buffer_size']}"
        )

    def test_duplicate_groups_have_required_fields(self):
        """Verify each duplicate group has all required fields."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        for group in report["duplicate_groups"]:
            assert "hash" in group
            assert "algo" in group
            assert "files" in group
            assert "total_size" in group
            assert "dedup_savings" in group

    def test_dedup_section_has_required_subfields(self):
        """Verify dedup section has all required subfields."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        dedup = report["dedup"]
        assert "duplicate_groups" in dedup
        assert "duplicate_files" in dedup
        assert "total_savings" in dedup
        assert "actions_taken" in dedup
        assert "total_removed" in dedup
        assert "dry_run" in dedup

    def test_config_fields_are_present(self):
        """Verify config section has all required fields."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        cfg = report["config"]
        assert "algorithm" in cfg
        assert "buffer_size" in cfg
        assert "keep_strategy" in cfg
        assert "follow_symlinks" in cfg
        assert "skip_hidden" in cfg
        assert "min_size" in cfg
        assert "max_size" in cfg
        assert "dry_run" in cfg
        assert "report_format" in cfg

    def test_config_dry_run_matches_expected(self):
        """Verify config.dry_run reflects always_dry_run (false by default)."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert report["config"]["dry_run"] is False

    def test_config_keep_strategy_is_present(self):
        """Verify config.keep_strategy is present and non-empty."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert len(report["config"]["keep_strategy"]) > 0


class TestScanErrors:
    """Tests for scan error handling."""

    def test_exit_code_1_on_missing_path(self):
        """Verify exit code 1 when a scan path does not exist."""
        result = _run_deduplicator(
            ["--paths", "/nonexistent/path_xyz", "--output", REPORT_PATH, "--dry-run"],
            check=False,
        )
        assert result.returncode == 1, (
            f"Expected exit code 1, got {result.returncode}"
        )

    def test_errors_list_populated_on_missing_path(self):
        """Verify errors array contains entry referencing the missing path."""
        missing = "/nonexistent/path_def"
        _run_deduplicator(
            ["--paths", missing, "--output", REPORT_PATH, "--dry-run"],
            check=False,
        )
        report = _load_report()
        assert len(report["errors"]) > 0, "Expected at least one error entry"
        combined_errors = " ".join(report["errors"]).lower()
        assert "path_def" in combined_errors, (
            f"Error messages should reference the missing path '{missing}', "
            f"got: {report['errors']}"
        )


class TestHashAlgorithm:
    """Tests for hash algorithm selection."""

    def test_default_hash_algorithm_is_sha256(self):
        """Verify default algorithm in config is sha256 when --hash-algo not passed."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert report["config"]["algorithm"] == "sha256", (
            f"Got '{report['config']['algorithm']}', expected 'sha256'"
        )

    def test_hashing_algo_reflects_resolved_algorithm(self):
        """Verify hashing.algo shows the actual resolved algorithm used, not raw config."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        assert report["hashing"]["algo"] == "sha256", (
            f"hashing.algo should be 'sha256', got '{report['hashing']['algo']}'"
        )

    def test_sha256_hash_is_64_hex_chars(self):
        """Verify SHA-256 digests are 64-character hex strings."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
        report = _load_report()
        has_sha256 = False
        for group in report["duplicate_groups"]:
            if group["algo"] == "sha256":
                has_sha256 = True
                assert len(group["hash"]) == 64, (
                    f"SHA-256 hash should be 64 chars, got {len(group['hash'])}"
                )
        assert has_sha256, "No SHA-256 groups found"

    def test_fallback_to_sha256_on_unknown_algorithm(self):
        """Verify unknown algorithm falls back to sha256."""
        _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run",
                          "--hash-algo", "nonexistent_algo_xyz"])
        report = _load_report()
        assert report["hashing"]["algo"] == "sha256", (
            f"Should fall back to sha256, got '{report['hashing']['algo']}'"
        )


class TestDeterminism:
    """Tests for deterministic output."""

    def test_deterministic_output(self):
        """Verify repeated runs produce identical output with sorted groups/files."""
        reports = []
        for _ in range(3):
            _run_deduplicator(["--paths", SAMPLE_DATA, "--output", REPORT_PATH, "--dry-run"])
            with open(REPORT_PATH) as f:
                reports.append(f.read())

        assert reports[0] == reports[1] == reports[2], "Non-deterministic output"

        report = _load_report()
        groups = report["duplicate_groups"]

        for i in range(len(groups) - 1):
            assert groups[i]["hash"] <= groups[i + 1]["hash"], (
                f"Groups not sorted: {groups[i]['hash']} > {groups[i+1]['hash']}"
            )

        for group in groups:
            files = group["files"]
            for i in range(len(files) - 1):
                assert files[i]["path"] <= files[i + 1]["path"], (
                    f"Files not sorted in group {group['hash']}"
                )
