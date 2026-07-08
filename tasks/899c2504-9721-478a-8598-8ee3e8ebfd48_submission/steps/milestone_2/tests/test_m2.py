"""Milestone 2: permission drift and harness alternate file rows."""
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
OUT = Path("/app/output/m2_permissions.json")

B_PROFILE = {"owner": "svc_rot", "group": "svc_rot", "mode": "0640"}


def copy_harness_base(tmp_root: Path) -> Path:
    base = tmp_root / "harness_base"
    for sub in ("config", "data"):
        shutil.copytree(_ENV_ROOT / sub, base / sub)
    return base


def run_cli_stage(base: Path, work_root: Path) -> dict:
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
            "m2",
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
    return json.loads((out / "m2_permissions.json").read_text(encoding="utf-8"))


def run_stage() -> dict:
    subprocess.run(["/app/environment/scripts/reset_workspace.sh"], check=True)
    subprocess.run(["/app/environment/tools/run_pipeline.sh", "--stage", "m2"], check=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone2:
    def test_drift_paths(self) -> None:
        """Drift captures mismatched ownership and modes; stage matches contract."""
        payload = run_stage()
        assert payload["stage"] == "m2"
        assert payload["drift"] == ["/opt/app/b.log", "/opt/app/c.log"]
        assert len(payload["drift_details"]) == 2

    def test_drift_details_structure_on_bundled_data(self) -> None:
        """Each drift_details row carries observed, expected, and mismatch_fields."""
        payload = run_stage()
        by_path = {row["path"]: row for row in payload["drift_details"]}
        b = by_path["/opt/app/b.log"]
        assert b["observed"] == {"owner": "svc_old", "group": "svc_old", "mode": "0600"}
        assert b["expected"] == B_PROFILE
        assert b["mismatch_fields"] == ["owner", "group", "mode"]
        c = by_path["/opt/app/c.log"]
        assert c["mismatch_fields"] == ["mode"]

    def test_ownership_state_complete(self) -> None:
        """ownership_state maps every file path to owner, group, and mode."""
        payload = run_stage()
        assert set(payload["ownership_state"].keys()) == {
            "/opt/app/a.log",
            "/opt/app/b.log",
            "/opt/app/c.log",
        }
        assert payload["ownership_state"]["/opt/app/a.log"] == B_PROFILE
        assert payload["mode_state"]["/opt/app/a.log"] == "0640"
        assert payload["mode_state"]["/opt/app/c.log"] == "0600"

    def test_harness_drift_follows_alternate_file_rows(self) -> None:
        """Stage m2 drift is recomputed from files.csv in the active base tree."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "files.csv").write_text(
                "path,owner,group,mode\n"
                "/opt/app/a.log,svc_rot,svc_rot,0640\n"
                "/opt/app/b.log,svc_old,svc_old,0600\n"
                "/opt/app/c.log,svc_rot,svc_rot,0640\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, work)
        assert payload["drift"] == ["/opt/app/b.log"]
        detail = payload["drift_details"][0]
        assert detail["path"] == "/opt/app/b.log"
        assert detail["mismatch_fields"] == ["owner", "group", "mode"]
