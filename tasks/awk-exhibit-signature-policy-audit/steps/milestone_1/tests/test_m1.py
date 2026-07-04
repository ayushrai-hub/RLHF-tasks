"""Milestone 1 tests: reconcile the stale database against the live Trust Registry."""

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
OUTPUT = APP / "output" / "signing_catalog.json"
SCHEMA = APP / "config" / "schemas" / "signing_catalog.schema.json"
PAGES_DIR = APP / "registry" / "pages"


def run_stage(stage: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(AUDIT), stage], text=True, capture_output=True, timeout=240, check=False)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def key_state(payload: dict) -> dict:
    return {im["key_id"]: (im["key_status"], im["key_trusted"], im["revocation_reason"]) for im in payload["images"]}


def pages() -> list[Path]:
    return sorted(PAGES_DIR.glob("keystates_page_*.json"))


class TestMilestone1:
    def test_catalog_runs(self) -> None:
        if OUTPUT.exists():
            OUTPUT.unlink()
        result = run_stage("catalog")
        assert result.returncode == 0, result.stderr
        assert OUTPUT.exists()

    def test_matches_schema(self) -> None:
        run_stage("catalog")
        jsonschema.validate(load(OUTPUT), load(SCHEMA))

    def test_matches_authority(self) -> None:
        run_stage("catalog")
        assert load(OUTPUT) == authority.build_catalog(APP)

    def test_reconciliation_discriminators(self) -> None:
        run_stage("catalog")
        st = key_state(load(OUTPUT))
        # a later revision whose as_of is in the future is not yet effective
        assert st["K-ED-C"] == ("active", True, None)
        # a voided key is expunged from trust
        assert st["K-EC-D"] == ("revoked", True, "key_expunged")
        # the highest effective revision reinstated the key
        assert st["K-ED-F"] == ("active", True, None)
        # the registry overrides the stale database snapshot
        assert st["K-RSA-B"] == ("revoked", True, "superseded")
        # a key absent from the registry keeps the database snapshot
        assert st["K-RSA-E"] == ("active", True, None)

    def test_reads_live_registry(self) -> None:
        backups = {p: p.read_bytes() for p in pages()}
        try:
            run_stage("catalog")
            before = key_state(load(OUTPUT))
            assert before["K-RSA-A"][0] == "active"
            for p in pages():
                page = json.loads(p.read_text(encoding="utf-8"))
                changed = False
                for rec in page["records"]:
                    if rec["key_id"] == "K-RSA-A":
                        rec["status"] = "revoked"
                        rec["revocation_reason"] = "cessation_of_operation"
                        rec["revoked_at"] = "2026-05-01T00:00:00Z"
                        changed = True
                if changed:
                    p.write_text(json.dumps(page), encoding="utf-8")
            run_stage("catalog")
            after = key_state(load(OUTPUT))
            assert after["K-RSA-A"][0] == "revoked"
        finally:
            for p, b in backups.items():
                p.write_bytes(b)
            run_stage("catalog")
