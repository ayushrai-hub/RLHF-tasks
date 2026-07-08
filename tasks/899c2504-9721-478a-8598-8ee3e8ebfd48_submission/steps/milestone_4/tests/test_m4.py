"""Milestone 4: audit summary."""
import hashlib
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
OUT = Path("/app/output/m4_audit.json")


def audit_digest_hex(summary: dict[str, int]) -> str:
    parts = [f"{key}:{summary[key]}" for key in sorted(summary)]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


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
            "m4",
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
    return json.loads((out / "m4_audit.json").read_text(encoding="utf-8"))


def run_stage() -> dict:
    subprocess.run(["/app/environment/scripts/reset_workspace.sh"], check=True)
    subprocess.run(["/app/environment/tools/run_pipeline.sh", "--stage", "m4"], check=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone4:
    def test_audit_summary(self) -> None:
        """Audit summary reflects unresolved drift and blocked restarts in bundled data."""
        payload = run_stage()
        assert payload["stage"] == "m4"
        assert payload["idempotent"] is False
        expected_summary = {"blocked": 1, "drift": 2, "gated": 1}
        assert payload["summary"] == expected_summary
        assert payload["digest"] == audit_digest_hex(expected_summary)

    def test_replay_stability(self) -> None:
        """Two consecutive m4 runs emit identical JSON."""
        first = run_stage()
        second = run_stage()
        assert first == second

    def test_harness_loader_normalizes_encoded_files_csv(self) -> None:
        """m4 still counts drift when files.csv uses literal \\n row separators."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "files.csv").write_bytes(
                b"path,owner,group,mode\\n"
                b"/opt/app/a.log,svc_rot,svc_rot,0640\\n"
                b"/opt/app/b.log,svc_old,svc_old,0600\\n"
                b"/opt/app/c.log,svc_rot,svc_rot,0600\\n"
            )
            (base / "data" / "services.csv").write_bytes(
                b"unit,ready,needs_restart\\n"
                b"rotate-api,yes,yes\\n"
                b"rotate-sync,no,yes\\n"
                b"rotate-audit,yes,no\\n"
            )
            payload = run_cli_stage(base, work)
        assert payload["summary"]["drift"] == 2
        assert payload["summary"]["blocked"] == 1
