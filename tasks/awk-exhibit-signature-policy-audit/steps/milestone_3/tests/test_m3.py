"""Milestone 3 tests: the remediation report stage."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import authority  # noqa: E402

APP = Path("/app")
AUDIT = APP / "bin" / "audit.sh"
OUTPUT = APP / "output" / "remediation_report.json"
SCHEMA = APP / "config" / "schemas" / "remediation_report.schema.json"
PAGES_DIR = APP / "registry" / "pages"


def run_stage(stage: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(AUDIT), stage], text=True, capture_output=True, timeout=240, check=False)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def expected() -> dict:
    return authority.compute_all(APP)["report"]


class TestMilestone3:
    def test_report_runs(self) -> None:
        if OUTPUT.exists():
            OUTPUT.unlink()
        result = run_stage("report")
        assert result.returncode == 0, result.stderr
        assert OUTPUT.exists()

    def test_matches_schema(self) -> None:
        run_stage("report")
        jsonschema.validate(load(OUTPUT), load(SCHEMA))

    def test_matches_authority(self) -> None:
        run_stage("report")
        assert load(OUTPUT) == expected()

    def test_discriminating_cases(self) -> None:
        run_stage("report")
        actions = {a["image_id"]: a for a in load(OUTPUT)["image_actions"]}
        # revoked (registry) key, authentic before revocation
        assert actions["IMG-002"]["action"] == "reinstate"
        # a later revoked revision is future-dated, so the key is still active
        assert actions["IMG-003"]["action"] == "accept"
        # voided key quarantines retroactively under key_expunged
        assert actions["IMG-005"]["action"] == "quarantine"
        assert actions["IMG-005"]["reason"] == "key_expunged"
        # reinstated key (latest registry revision) is active again
        assert actions["IMG-010"]["action"] == "accept"
        # same key as IMG-002, signed after the revocation instant
        assert actions["IMG-011"]["action"] == "quarantine"
        assert actions["IMG-011"]["reason"] == "signed_after_revocation"

    def test_registry_drives_report(self) -> None:
        backups = {p: p.read_bytes() for p in sorted(PAGES_DIR.glob("keystates_page_*.json"))}
        try:
            run_stage("report")
            before = {a["image_id"]: a["action"] for a in load(OUTPUT)["image_actions"]}
            assert before["IMG-001"] == "accept"
            for p in backups:
                page = json.loads(p.read_text(encoding="utf-8"))
                changed = False
                for rec in page["records"]:
                    if rec["key_id"] == "K-RSA-A":
                        rec["status"] = "revoked"
                        rec["revocation_reason"] = "key_compromise"
                        rec["revoked_at"] = "2025-06-01T00:00:00Z"
                        changed = True
                if changed:
                    p.write_text(json.dumps(page), encoding="utf-8")
            run_stage("report")
            after = {a["image_id"]: a for a in load(OUTPUT)["image_actions"]}
            assert after["IMG-001"]["action"] == "quarantine"
            assert after["IMG-001"]["reason"] == "key_compromise"
        finally:
            for p, b in backups.items():
                p.write_bytes(b)
            run_stage("report")
