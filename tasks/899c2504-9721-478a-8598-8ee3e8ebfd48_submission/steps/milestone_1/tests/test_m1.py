"""Milestone 1: plan stage and harness alternate bases."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_container_src = Path("/app/environment/src")
if _container_src.is_dir():
    _ENV_SRC = str(_container_src)
else:
    _ENV_SRC = str(Path(__file__).resolve().parents[3] / "environment" / "src")
if _ENV_SRC not in sys.path:
    sys.path.insert(0, _ENV_SRC)
_ENV_ROOT = Path("/app/environment") if _container_src.is_dir() else Path(__file__).resolve().parents[3] / "environment"

_CLI_ENV = {**os.environ, "PYTHONPATH": _ENV_SRC}
OUT = Path("/app/output/m1_plan.json")


def copy_harness_base(tmp_root: Path) -> Path:
    base = tmp_root / "harness_base"
    for sub in ("config", "data"):
        shutil.copytree(_ENV_ROOT / sub, base / sub)
    return base


def run_cli_stage(base: Path, stage: str, work_root: Path) -> dict:
    out = work_root / "out"
    state = work_root / "state"
    out.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "python3",
            "-m",
            "pipeline.cli",
            "--stage",
            stage,
            "--base",
            str(base),
            "--output",
            str(out),
            "--state",
            str(state),
        ],
        check=True,
        env=_CLI_ENV,
    )
    name = {"m1": "m1_plan.json", "m2": "m2_permissions.json", "m3": "m3_services.json", "m4": "m4_audit.json"}[stage]
    return json.loads((out / name).read_text(encoding="utf-8"))


def run_stage() -> dict:
    subprocess.run(["/app/environment/scripts/reset_workspace.sh"], check=True)
    subprocess.run(["/app/environment/tools/run_pipeline.sh", "--stage", "m1"], check=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone1:
    def test_targets_and_actions(self) -> None:
        """Plan includes stage, rotation_epoch, all files, and expected actions."""
        payload = run_stage()
        assert payload["stage"] == "m1"
        assert payload["rotation_epoch"] == "2026-05"
        assert payload["targets"] == ["/opt/app/a.log", "/opt/app/b.log", "/opt/app/c.log"]
        assert payload["actions"] == ["chown", "chmod", "restart"]

    def test_target_count_matches_targets(self) -> None:
        """target_count equals the number of file rows ingested."""
        payload = run_stage()
        assert payload["target_count"] == 3
        assert payload["target_count"] == len(payload["targets"])

    def test_harness_rotation_epoch_from_live_config(self) -> None:
        """Stage m1 reads rotation_epoch from the active state_rules.toml."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "config" / "state_rules.toml").write_text(
                'rotation_epoch = "TB3-HARNESS-77"\n',
                encoding="utf-8",
            )
            payload = run_cli_stage(base, "m1", work)
        assert payload["rotation_epoch"] == "TB3-HARNESS-77"

    def test_harness_action_dedupe_from_rotation_file(self) -> None:
        """Stage m1 dedupes rotation_actions.txt while preserving first-seen order."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "rotation_actions.txt").write_text(
                "chown\nchmod\nchmod\nrestart\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, "m1", work)
        assert payload["actions"] == ["chown", "chmod", "restart"]

    def test_harness_targets_from_live_csv(self) -> None:
        """targets follow rows from the active files.csv, not bundled literals."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "files.csv").write_text(
                "path,owner,group,mode\n/x/y.log,root,root,0644\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, "m1", work)
        assert payload["targets"] == ["/x/y.log"]
        assert payload["target_count"] == 1

    def test_harness_literal_backslash_n_normalization(self) -> None:
        """Loader normalizes literal two-character \\n between rotation action rows."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "rotation_actions.txt").write_bytes(b"chown\\nchmod\\nrestart\\n")
            payload = run_cli_stage(base, "m1", work)
        assert payload["actions"] == ["chown", "chmod", "restart"]
