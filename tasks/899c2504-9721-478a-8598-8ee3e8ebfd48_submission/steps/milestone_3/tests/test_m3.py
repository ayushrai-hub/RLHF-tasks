"""Milestone 3: service restart gates."""
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
OUT = Path("/app/output/m3_services.json")


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
            "m3",
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
    return json.loads((out / "m3_services.json").read_text(encoding="utf-8"))


def run_stage() -> dict:
    subprocess.run(["/app/environment/scripts/reset_workspace.sh"], check=True)
    subprocess.run(["/app/environment/tools/run_pipeline.sh", "--stage", "m3"], check=True)
    return json.loads(OUT.read_text(encoding="utf-8"))


class TestMilestone3:
    def test_restart_gates(self) -> None:
        """restart_plan equals gated_units; blocked units stay out of restart_plan."""
        payload = run_stage()
        assert payload["stage"] == "m3"
        assert payload["gated_units"] == ["rotate-api"]
        assert payload["blocked_units"] == ["rotate-sync"]
        assert payload["restart_plan"] == payload["gated_units"]
        assert "rotate-sync" not in payload["restart_plan"]

    def test_harness_restart_tokens_and_order(self) -> None:
        """Readiness aliases gate units in service_rules.toml order."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "services.csv").write_text(
                "unit,ready,needs_restart\n"
                "rotate-audit,1,no\n"
                "rotate-sync,ready,yes\n"
                "rotate-api,true,yes\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, work)
        assert payload["gated_units"] == ["rotate-api", "rotate-sync"]
        assert payload["blocked_units"] == []
        assert payload["restart_plan"] == ["rotate-api", "rotate-sync"]

    def test_harness_literal_newlines_in_services_csv(self) -> None:
        """services.csv stored with literal \\n still parses for gating."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "services.csv").write_bytes(
                b"unit,ready,needs_restart\\n"
                b"rotate-api,yes,yes\\n"
                b"rotate-sync,no,yes\\n"
                b"rotate-audit,yes,no\\n"
            )
            payload = run_cli_stage(base, work)
        assert payload["gated_units"] == ["rotate-api"]
        assert payload["restart_plan"] == ["rotate-api"]

    def test_harness_readiness_one_gates_restart(self) -> None:
        """Readiness token 1 counts as yes and gates restart when needs_restart is yes."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "services.csv").write_text(
                "unit,ready,needs_restart\n"
                "rotate-api,1,yes\n"
                "rotate-sync,no,yes\n"
                "rotate-audit,no,no\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, work)
        assert payload["gated_units"] == ["rotate-api"]
        assert payload["restart_plan"] == ["rotate-api"]
        assert "rotate-sync" in payload["blocked_units"]
        assert "rotate-sync" not in payload["restart_plan"]

    def test_harness_readiness_y_gates_restart(self) -> None:
        """Readiness token y counts as yes after trim and lowercasing."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "services.csv").write_text(
                "unit,ready,needs_restart\n"
                "rotate-api, Y ,yes\n"
                "rotate-sync,no,yes\n"
                "rotate-audit,no,no\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, work)
        assert payload["gated_units"] == ["rotate-api"]
        assert payload["restart_plan"] == ["rotate-api"]
        assert "rotate-sync" not in payload["restart_plan"]

    def test_harness_allowlist_exclusion(self) -> None:
        """Units absent from units_allowlist.txt are never placed in restart_plan."""
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            base = copy_harness_base(work)
            (base / "data" / "units_allowlist.txt").write_text(
                "rotate-api\nrotate-audit\n",
                encoding="utf-8",
            )
            (base / "data" / "services.csv").write_text(
                "unit,ready,needs_restart\n"
                "rotate-api,yes,yes\n"
                "rotate-sync,yes,yes\n"
                "rotate-audit,no,no\n",
                encoding="utf-8",
            )
            payload = run_cli_stage(base, work)
        assert payload["gated_units"] == ["rotate-api"]
        assert payload["restart_plan"] == ["rotate-api"]
        assert "rotate-sync" not in payload["gated_units"]
        assert "rotate-sync" not in payload["restart_plan"]
