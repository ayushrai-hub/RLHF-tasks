"""Milestone 2 tests: the signature evidence stage."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
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
OUTPUT = APP / "output" / "signature_evidence.json"
SCHEMA = APP / "config" / "schemas" / "signature_evidence.schema.json"


def run_stage(stage: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([str(AUDIT), stage], text=True, capture_output=True, timeout=240, check=False)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def expected() -> dict:
    cfg = authority.load_config(APP)
    return authority.build_evidence(APP, authority.build_catalog(APP, cfg), cfg)


class TestMilestone2:
    def test_verify_runs(self) -> None:
        if OUTPUT.exists():
            OUTPUT.unlink()
        result = run_stage("verify")
        assert result.returncode == 0, result.stderr
        assert OUTPUT.exists()

    def test_matches_schema(self) -> None:
        run_stage("verify")
        jsonschema.validate(load(OUTPUT), load(SCHEMA))

    def test_matches_authority(self) -> None:
        run_stage("verify")
        assert load(OUTPUT) == expected()

    def test_method_fingerprint_and_content(self) -> None:
        run_stage("verify")
        ev = {e["image_id"]: e for e in load(OUTPUT)["evidence"]}
        exp = {e["image_id"]: e for e in expected()["evidence"]}
        for image_id, entry in ev.items():
            assert entry["verify_method"] == exp[image_id]["verify_method"]
            assert entry["computed_fingerprint"] == exp[image_id]["computed_fingerprint"]
            assert entry["fingerprint_match"] == exp[image_id]["fingerprint_match"]
            assert entry["content_sha256"] == exp[image_id]["content_sha256"]

    def test_fingerprint_gate(self) -> None:
        run_stage("verify")
        ev = {e["image_id"]: e for e in load(OUTPUT)["evidence"]}
        assert ev["IMG-009"]["fingerprint_match"] is False
        assert ev["IMG-009"]["signature_valid"] is False
        assert ev["IMG-009"]["failure_reason"] == "fingerprint_mismatch"

    def test_content_binds_media(self) -> None:
        run_stage("verify")
        ev = {e["image_id"]: e for e in load(OUTPUT)["evidence"]}
        for e in ev.values():
            media = APP / "data" / "media" / f"{e['image_id']}.png"
            assert e["content_sha256"] == hashlib.sha256(media.read_bytes()).hexdigest()

    def test_tamper_flips_validity(self) -> None:
        media = APP / "data" / "media" / "IMG-001.png"
        backup = media.with_suffix(".png.m2bak")
        shutil.copy2(media, backup)
        try:
            run_stage("verify")
            before = {e["image_id"]: e for e in load(OUTPUT)["evidence"]}
            assert before["IMG-001"]["signature_valid"] is True
            media.write_bytes(media.read_bytes() + b"\x00tamper")
            run_stage("verify")
            after = {e["image_id"]: e for e in load(OUTPUT)["evidence"]}
            assert after["IMG-001"]["signature_valid"] is False
            assert after["IMG-001"]["failure_reason"] == "signature_verification_failed"
        finally:
            shutil.move(backup, media)
            run_stage("verify")
