import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


APP = Path(os.environ.get("APP_UNDER_TEST", "/app"))
BASE_INPUT = APP / "fixtures"
BASE_OUTPUT = APP / "output"

EXPECTED_BASE = {
    "alice": ("admin", 3),
    "bob": ("maintainer", 8),
    "carol": ("readonly", 5),
}

EXPECTED_GEN_7 = {
    "alice": ("admin", 1),
    "bob": ("operator", 2),
}


def _run(input_dir=BASE_INPUT, output_dir=BASE_OUTPUT):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "src/reload.ts",
            "--input",
            str(input_dir),
            "--output",
            str(output_dir),
        ],
        cwd=APP,
        check=True,
    )
    return _load_outputs(output_dir)


def _load_outputs(output_dir):
    return {
        "plan": json.loads((output_dir / "policy_plan.json").read_text(encoding="utf-8")),
        "revoked": json.loads((output_dir / "revoke_manifest.json").read_text(encoding="utf-8")),
        "report": json.loads((output_dir / "reload_report.json").read_text(encoding="utf-8")),
    }


def _entries_by_user(plan):
    return {entry["user"]: entry for entry in plan["entries"]}


def _plan_digest(entries):
    lines = [
        f'{entry["user"]}|{entry["role"]}|{entry["seq"]}|{entry["action"]}'
        for entry in sorted(entries, key=lambda item: item["user"])
    ]
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[-8:]


def _output_digest(output_dir):
    h = hashlib.sha256()
    for file in sorted(output_dir.glob("*.json")):
        h.update(file.name.encode("utf-8"))
        h.update(file.read_bytes())
    return h.hexdigest()


def _assert_entries(plan, expected):
    assert [entry["user"] for entry in plan["entries"]] == sorted(expected)
    entries = _entries_by_user(plan)
    for user, (role, seq) in expected.items():
        entry = entries[user]
        assert entry["role"] == role
        assert entry["seq"] == seq
        assert entry["action"] == "allow-user"


def test_base_policy_plan_uses_active_generation_audit_and_revokes():
    """Verify plan entries derive from gen-8 audit records and revoked users stay out of the plan."""
    outputs = _run()
    plan = outputs["plan"]
    revoked = outputs["revoked"]

    assert plan["generation"] == "gen-8"
    _assert_entries(plan, EXPECTED_BASE)
    assert "dan" not in _entries_by_user(plan)

    assert revoked["generation"] == "gen-8"
    assert revoked["revoked"] == [{"user": "dan", "seq": 7}]


def test_report_matches_public_contract():
    """Verify reload_report summary and checks match the generated plan and revoke manifest."""
    outputs = _run()
    plan = outputs["plan"]
    revoked = outputs["revoked"]
    report = outputs["report"]

    assert report["summary"]["unit"] == "ssh-bastion.service"
    assert report["summary"]["generation"] == "gen-8"
    assert report["summary"]["entries_total"] == len(plan["entries"])
    assert report["summary"]["revoked_total"] == len(revoked["revoked"])
    assert report["summary"]["reload_status"] == "settled"
    assert report["summary"]["plan_digest"] == _plan_digest(plan["entries"])
    assert report["checks"] == {
        "user_map_complete": True,
        "audit_trail_aligned": True,
        "revokes_respected": True,
        "idempotent_plan": True,
    }


def test_driver_output_is_idempotent():
    """A second driver run must leave all output JSON byte-identical."""
    _run()
    first = _output_digest(BASE_OUTPUT)
    subprocess.run(
        [
            "node",
            "--experimental-strip-types",
            "src/reload.ts",
            "--input",
            str(BASE_INPUT),
            "--output",
            str(BASE_OUTPUT),
        ],
        cwd=APP,
        check=True,
    )
    assert first == _output_digest(BASE_OUTPUT)


def test_variant_generation_follows_fixture_state(tmp_path):
    """Changing active generation must re-derive plan and revoke manifest from that generation only."""
    variant_input = tmp_path / "fixtures"
    variant_output = tmp_path / "output"
    shutil.copytree(BASE_INPUT, variant_input)
    (variant_input / "reload-state.env").write_text(
        "unit=ssh-bastion.service\nactive_generation=gen-7\ncheckpoint_seq=2\n",
        encoding="utf-8",
    )

    outputs = _run(variant_input, variant_output)
    plan = outputs["plan"]
    revoked = outputs["revoked"]
    report = outputs["report"]

    assert plan["generation"] == "gen-7"
    _assert_entries(plan, EXPECTED_GEN_7)
    assert revoked["generation"] == "gen-7"
    assert revoked["revoked"] == []
    assert report["summary"]["generation"] == "gen-7"
    assert report["summary"]["entries_total"] == len(EXPECTED_GEN_7)
    assert report["summary"]["revoked_total"] == 0
    assert report["summary"]["plan_digest"] == _plan_digest(plan["entries"])
