import json
import shutil
import subprocess
from pathlib import Path

APP = Path("/app/environment")
AUTHZCTL = "/app/environment/bin/authzctl"
OUTDIR = Path("/app/output")
WORK = Path("/tmp/authz-checker")


def build_binary():
    subprocess.run(["make", "-C", "/app/environment", "build"], check=True)
    assert Path(AUTHZCTL).exists(), "make build must produce /app/environment/bin/authzctl"


def _run_authzctl(args, cwd=APP):
    subprocess.run(["/app/environment/bin/authzctl", *args], cwd=cwd, check=True)


def run_case(name, scenario, resume=False, state_dir=None):
    build_binary()
    case_dir = WORK / name
    if state_dir is None:
        state_dir = case_dir / "state"
    out_path = OUTDIR / f"{name}.json"
    if not resume and case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    OUTDIR.mkdir(parents=True, exist_ok=True)
    scenario_path = case_dir / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    args = [
        "run-case",
        "--case",
        str(scenario_path),
        "--state",
        str(state_dir),
        "--out",
        str(out_path),
    ]
    if resume:
        args.append("--resume")
    _run_authzctl(args)
    return json.loads(out_path.read_text(encoding="utf-8")), scenario_path, state_dir, out_path


def run_until_step(name, scenario, stop_step):
    build_binary()
    case_dir = WORK / f"{name}-partial"
    state_dir = case_dir / "state"
    out_path = OUTDIR / f"{name}-partial.json"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = case_dir / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    _run_authzctl(
        [
            "run-case",
            "--case",
            str(scenario_path),
            "--state",
            str(state_dir),
            "--out",
            str(out_path),
            "--stop-after-step",
            str(stop_step),
        ]
    )
    resume_out = OUTDIR / f"{name}-resume.json"
    _run_authzctl(
        [
            "run-case",
            "--case",
            str(scenario_path),
            "--state",
            str(state_dir),
            "--out",
            str(resume_out),
            "--resume",
        ]
    )
    return (
        json.loads(resume_out.read_text(encoding="utf-8")),
        scenario_path,
        state_dir,
        resume_out,
    )


def run_segmented_resume(name, scenario, stop_steps):
    build_binary()
    case_dir = WORK / name
    state_dir = case_dir / "state"
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = case_dir / "scenario.json"
    scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    traces = []
    for stop in stop_steps:
        out_path = OUTDIR / f"{name}-stop-{stop}.json"
        _run_authzctl(
            [
                "run-case",
                "--case",
                str(scenario_path),
                "--state",
                str(state_dir),
                "--out",
                str(out_path),
                "--stop-after-step",
                str(stop),
            ]
        )
        resume_out = OUTDIR / f"{name}-resume-{stop}.json"
        _run_authzctl(
            [
                "run-case",
                "--case",
                str(scenario_path),
                "--state",
                str(state_dir),
                "--out",
                str(resume_out),
                "--resume",
            ]
        )
        traces.append(json.loads(resume_out.read_text(encoding="utf-8")))
    final_out = OUTDIR / f"{name}-final.json"
    _run_authzctl(
        [
            "run-case",
            "--case",
            str(scenario_path),
            "--state",
            str(state_dir),
            "--out",
            str(final_out),
            "--resume",
        ]
    )
    final_trace = json.loads(final_out.read_text(encoding="utf-8"))
    return final_trace, traces, scenario_path, state_dir


def decision(trace, username, resource, action, tick):
    matches = [
        d
        for d in trace["decisions"]
        if d["username"] == username and d["resource"] == resource and d["action"] == action and d["tick"] == tick
    ]
    assert len(matches) == 1, f"expected one decision for {username} {resource}:{action} at tick {tick}, got {matches}"
    return matches[0]


def cache_entry(trace, username):
    matches = [entry for entry in trace["cache_entries"] if entry["username"] == username]
    assert len(matches) == 1, f"expected one cache entry for {username}, got {matches}"
    return matches[0]


def indexed_members(trace, group):
    for row in trace["group_index"]:
        if row["group"] == group:
            return {(m["username"], m["subject_id"], m["generation"]) for m in row["members"]}
    return set()


def normalize_entries(entries):
    return sorted(entries, key=lambda e: e["username"])


def normalize_index(rows):
    out = []
    for row in sorted(rows, key=lambda r: r["group"]):
        members = sorted(row["members"], key=lambda m: (m["username"], m["subject_id"]))
        out.append({"group": row["group"], "members": members})
    return out


def load_manifest(state_dir):
    return json.loads((state_dir / "run_manifest.json").read_text(encoding="utf-8"))


def load_journal(state_dir):
    path = state_dir / "refresh_journal.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def base_resources(group):
    return [{"id": "resource", "actions": {"use": [group]}}]


class TestAuthorizationCacheRevocation:
    def test_chained_reject_reaccept_resume_coherence(self):
        """Reject, republish with a valid proof, reaccept, and resume must converge with journal and disk surfaces."""
        scenario = {
            "name": "generated-chained-reject-reaccept",
            "freshness_bound": 3,
            "resources": base_resources("ops") + [{"id": "vault", "actions": {"read": ["vault"]}}],
            "snapshots": [
                {
                    "revision": 400,
                    "proof": {"revision": 400, "issued_at": 0, "nonce": "r400"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["ops", "vault"], "active": True},
                    ],
                },
                {
                    "revision": 401,
                    "proof": {"revision": 400, "issued_at": 1, "nonce": "replayed-r400"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": [], "active": False},
                    ],
                },
                {
                    "revision": 402,
                    "proof": {"revision": 402, "issued_at": 2, "nonce": "r402"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["vault"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 400},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ava", "resource": "vault", "action": "read"},
                {"op": "publish", "tick": 1, "revision": 401},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "ava", "resource": "vault", "action": "read"},
                {"op": "publish", "tick": 2, "revision": 402},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 2, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 2, "username": "ava", "resource": "vault", "action": "read"},
            ],
        }
        full_trace, _, _, _ = run_case("chain-mono", scenario)
        resume_trace, _, state_dir, _ = run_until_step("chain-split", scenario, stop_step=6)
        assert decision(full_trace, "ava", "vault", "read", 0)["result"] == "allow"
        assert decision(full_trace, "ava", "vault", "read", 1)["result"] == "deny"
        assert decision(full_trace, "ava", "resource", "use", 2)["result"] == "deny"
        assert decision(full_trace, "ava", "vault", "read", 2)["result"] == "allow"
        assert decision(resume_trace, "ava", "vault", "read", 2)["result"] == "allow"
        assert normalize_entries(full_trace["cache_entries"]) == normalize_entries(resume_trace["cache_entries"])
        assert normalize_index(full_trace["group_index"]) == normalize_index(resume_trace["group_index"])
        journal = load_journal(state_dir)
        assert len(journal) == 3
        assert journal[1]["accepted"] is False
        assert journal[1]["reason"] == "proof-revision-mismatch"
        assert journal[2]["accepted"] is True
        manifest = load_manifest(state_dir)
        assert manifest["completed_step"] == len(scenario["steps"])
        assert manifest["refresh_epoch"] == 2
        assert manifest["last_refresh_accepted"] is True
        assert ("ava", "ava-1", 1) not in indexed_members(resume_trace, "ops")
        assert ("ava", "ava-1", 1) in indexed_members(resume_trace, "vault")
        disk_index = json.loads((state_dir / "group_index.json").read_text(encoding="utf-8"))
        assert normalize_index(resume_trace["group_index"]) == normalize_index(disk_index)

    def test_staggered_proof_expiry_multi_user(self):
        """Proof age and refresh epochs must be evaluated per principal, not as one shared clock."""
        delayed = {
            "name": "generated-delayed-proof-age",
            "freshness_bound": 2,
            "resources": [{"id": "ledger", "actions": {"post": ["finance"]}}],
            "snapshots": [
                {
                    "revision": 610,
                    "proof": {"revision": 610, "issued_at": 0, "nonce": "r610"},
                    "principals": [
                        {"username": "sana", "subject_id": "subj-sana", "generation": 1, "groups": ["finance"], "active": True},
                    ],
                }
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 610},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 2, "username": "sana", "resource": "ledger", "action": "post"},
                {"op": "authorize", "tick": 3, "username": "sana", "resource": "ledger", "action": "post"},
            ],
        }
        delayed_trace, _, _, _ = run_case("delayed", delayed)
        early = decision(delayed_trace, "sana", "ledger", "post", 2)
        late = decision(delayed_trace, "sana", "ledger", "post", 3)
        assert early["result"] == "allow"
        assert late["result"] == "deny", late
        assert late["reason"] == "proof-expired-at-authorize"
        assert late["proof_age"] == 3

        split_epoch = {
            "name": "generated-split-epoch-principals",
            "freshness_bound": 3,
            "resources": [
                {"id": "ledger", "actions": {"post": ["finance"]}},
                {"id": "cluster", "actions": {"admin": ["rooters"]}},
            ],
            "snapshots": [
                {
                    "revision": 620,
                    "proof": {"revision": 620, "issued_at": 0, "nonce": "r620"},
                    "principals": [
                        {"username": "sana", "subject_id": "subj-sana", "generation": 1, "groups": ["finance"], "active": True},
                        {"username": "ren", "subject_id": "subj-ren-old", "generation": 1, "groups": ["rooters"], "active": True},
                    ],
                },
                {
                    "revision": 621,
                    "proof": {"revision": 621, "issued_at": 2, "nonce": "r621"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-old", "generation": 1, "groups": ["rooters"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 620},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "sana", "resource": "ledger", "action": "post"},
                {"op": "authorize", "tick": 0, "username": "ren", "resource": "cluster", "action": "admin"},
                {"op": "publish", "tick": 2, "revision": 621},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 3, "username": "ren", "resource": "cluster", "action": "admin"},
                {"op": "authorize", "tick": 3, "username": "sana", "resource": "ledger", "action": "post"},
            ],
        }
        split_trace, _, _, _ = run_case("split-epoch", split_epoch)
        assert decision(split_trace, "ren", "cluster", "admin", 3)["result"] == "allow"
        denied = decision(split_trace, "sana", "ledger", "post", 3)
        assert denied["result"] == "deny", denied
        assert denied["reason"] == "revoked-principal"
        assert cache_entry(split_trace, "ren")["refresh_epoch"] == 2
        assert cache_entry(split_trace, "sana")["refresh_epoch"] == 2
        assert cache_entry(split_trace, "sana")["revoked"] is True

    def test_replay_reject_then_republish_reaccept(self):
        """After a rejected replay refresh, a later valid republish must rebuild cache and index without ghost groups."""
        scenario = {
            "name": "generated-republish-reaccept",
            "freshness_bound": 2,
            "resources": base_resources("ops") + [{"id": "payroll", "actions": {"export": ["finance"]}}],
            "snapshots": [
                {
                    "revision": 310,
                    "proof": {"revision": 310, "issued_at": 0, "nonce": "r310"},
                    "principals": [
                        {"username": "sana", "subject_id": "subj-sana", "generation": 1, "groups": ["finance", "ops"], "active": True},
                    ],
                },
                {
                    "revision": 311,
                    "proof": {"revision": 310, "issued_at": 1, "nonce": "replayed-r310"},
                    "principals": [
                        {"username": "sana", "subject_id": "subj-sana", "generation": 1, "groups": [], "active": False},
                    ],
                },
                {
                    "revision": 312,
                    "proof": {"revision": 312, "issued_at": 2, "nonce": "r312"},
                    "principals": [
                        {"username": "sana", "subject_id": "subj-sana", "generation": 1, "groups": ["finance"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 310},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "sana", "resource": "payroll", "action": "export"},
                {"op": "publish", "tick": 1, "revision": 311},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "sana", "resource": "payroll", "action": "export"},
                {"op": "publish", "tick": 2, "revision": 312},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 2, "username": "sana", "resource": "payroll", "action": "export"},
                {"op": "authorize", "tick": 2, "username": "sana", "resource": "resource", "action": "use"},
            ],
        }
        trace, _, state_dir, _ = run_case("republish", scenario)
        assert decision(trace, "sana", "payroll", "export", 0)["result"] == "allow"
        assert decision(trace, "sana", "payroll", "export", 1)["result"] == "deny"
        assert decision(trace, "sana", "payroll", "export", 2)["result"] == "allow"
        assert decision(trace, "sana", "resource", "use", 2)["result"] == "deny"
        assert trace["refreshes"][1]["accepted"] is False
        assert ("sana", "subj-sana", 1) not in indexed_members(trace, "ops")
        assert ("sana", "subj-sana", 1) in indexed_members(trace, "finance")
        entry = cache_entry(trace, "sana")
        assert entry["refresh_epoch"] == 2
        assert entry["groups"] == ["finance"]
        journal = load_journal(state_dir)
        assert len(journal) == 3
        assert journal[1]["accepted"] is False
        assert journal[2]["accepted"] is True
        disk_index = json.loads((state_dir / "group_index.json").read_text(encoding="utf-8"))
        assert all(member["username"] != "sana" or member["subject_id"] == "subj-sana" for row in disk_index for member in row["members"])
        assert ("sana", "subj-sana", 1) not in {(m["username"], m["subject_id"], m["generation"]) for row in disk_index for m in row["members"] if row["group"] == "ops"}

    def test_subject_lineage_dual_resume_boundaries(self):
        """Username lineage across two resume boundaries must not inherit stale subject membership."""
        scenario = {
            "name": "generated-lineage-dual-resume",
            "freshness_bound": 4,
            "resources": [
                {"id": "cluster", "actions": {"admin": ["rooters"]}},
                {"id": "archive", "actions": {"read": ["readers"]}},
            ],
            "snapshots": [
                {
                    "revision": 730,
                    "proof": {"revision": 730, "issued_at": 0, "nonce": "r730"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-old", "generation": 1, "groups": ["rooters"], "active": True},
                    ],
                },
                {
                    "revision": 731,
                    "proof": {"revision": 731, "issued_at": 1, "nonce": "r731"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-new", "generation": 2, "groups": ["readers"], "active": True},
                    ],
                },
                {
                    "revision": 732,
                    "proof": {"revision": 732, "issued_at": 2, "nonce": "r732"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-third", "generation": 3, "groups": ["rooters"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 730},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ren", "resource": "cluster", "action": "admin"},
                {"op": "publish", "tick": 1, "revision": 731},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "ren", "resource": "cluster", "action": "admin"},
                {"op": "authorize", "tick": 1, "username": "ren", "resource": "archive", "action": "read"},
                {"op": "publish", "tick": 2, "revision": 732},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 2, "username": "ren", "resource": "cluster", "action": "admin"},
            ],
        }
        mono_trace, _, _, _ = run_case("lineage-mono", scenario)
        final_trace, segment_traces, _, state_dir = run_segmented_resume("lineage", scenario, stop_steps=[3, 6])
        assert decision(mono_trace, "ren", "cluster", "admin", 0)["result"] == "allow"
        gen2_cluster = decision(mono_trace, "ren", "cluster", "admin", 1)
        gen2_archive = decision(mono_trace, "ren", "archive", "read", 1)
        gen3_cluster = decision(mono_trace, "ren", "cluster", "admin", 2)
        assert gen2_cluster["result"] == "deny", gen2_cluster
        assert gen2_cluster["subject_id"] == "subj-ren-new"
        assert gen2_archive["result"] == "allow", gen2_archive
        assert gen3_cluster["result"] == "allow", gen3_cluster
        assert gen3_cluster["subject_id"] == "subj-ren-third"
        assert normalize_entries(mono_trace["cache_entries"]) == normalize_entries(final_trace["cache_entries"])
        assert normalize_index(mono_trace["group_index"]) == normalize_index(final_trace["group_index"])
        assert ("ren", "subj-ren-old", 1) not in indexed_members(final_trace, "rooters")
        assert ("ren", "subj-ren-new", 2) not in indexed_members(final_trace, "rooters")
        assert ("ren", "subj-ren-third", 3) in indexed_members(final_trace, "rooters")
        assert segment_traces[0]["provenance"]["resume"]["used"] is True
        assert segment_traces[1]["provenance"]["resume"]["used"] is True
        entry = cache_entry(final_trace, "ren")
        assert entry["generation"] == 3
        assert entry["refresh_epoch"] == 3
        manifest = load_manifest(state_dir)
        assert manifest["refresh_epoch"] == 3

    def test_quad_resume_epoch_and_digest_continuity(self):
        """Four resume boundaries must preserve epoch_start, case digest, and final durable surfaces."""
        scenario = {
            "name": "generated-quad-resume",
            "freshness_bound": 5,
            "resources": base_resources("ops") + [{"id": "desk", "actions": {"open": ["staff"]}}],
            "snapshots": [
                {
                    "revision": 910,
                    "proof": {"revision": 910, "issued_at": 0, "nonce": "r910"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["ops"], "active": True},
                        {"username": "bo", "subject_id": "bo-1", "generation": 1, "groups": ["staff"], "active": True},
                    ],
                },
                {
                    "revision": 911,
                    "proof": {"revision": 911, "issued_at": 2, "nonce": "r911"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["ops"], "active": True},
                        {"username": "bo", "subject_id": "bo-1", "generation": 1, "groups": [], "active": False},
                    ],
                },
                {
                    "revision": 912,
                    "proof": {"revision": 912, "issued_at": 4, "nonce": "r912"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": [], "active": False},
                        {"username": "bo", "subject_id": "bo-1", "generation": 1, "groups": ["staff"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 910},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 0, "username": "bo", "resource": "desk", "action": "open"},
                {"op": "publish", "tick": 2, "revision": 911},
                {"op": "refresh", "tick": 2},
                {"op": "authorize", "tick": 2, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 2, "username": "bo", "resource": "desk", "action": "open"},
                {"op": "publish", "tick": 4, "revision": 912},
                {"op": "refresh", "tick": 4},
                {"op": "authorize", "tick": 4, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 4, "username": "bo", "resource": "desk", "action": "open"},
            ],
        }
        full_trace, scenario_path, _, _ = run_case("quad-mono", scenario)
        resume_trace, _, state_dir, _ = run_until_step("quad-split", scenario, stop_step=9)
        digest = subprocess.check_output(["sha256sum", str(scenario_path)], text=True).split()[0]
        assert resume_trace["provenance"]["case_digest"] == digest
        assert normalize_entries(full_trace["cache_entries"]) == normalize_entries(resume_trace["cache_entries"])
        assert normalize_index(full_trace["group_index"]) == normalize_index(resume_trace["group_index"])
        assert decision(full_trace, "ava", "resource", "use", 4)["result"] == "deny"
        assert decision(full_trace, "bo", "desk", "open", 4)["result"] == "allow"
        assert cache_entry(resume_trace, "ava")["revoked"] is True
        assert cache_entry(resume_trace, "bo")["revoked"] is False
        manifest = load_manifest(state_dir)
        assert manifest["completed_step"] == len(scenario["steps"])
        assert manifest["refresh_epoch"] == 3
        assert resume_trace["provenance"]["resume"]["used"] is True
        assert resume_trace["provenance"]["resume"]["epoch_start"] == 2

    def test_poisoned_index_and_manifest_epoch_recovery(self):
        """Resume must rebuild derived state when both the on-disk index and manifest epoch are poisoned."""
        scenario = {
            "name": "generated-poisoned-surfaces",
            "freshness_bound": 3,
            "resources": [{"id": "cluster", "actions": {"admin": ["rooters"]}}],
            "snapshots": [
                {
                    "revision": 740,
                    "proof": {"revision": 740, "issued_at": 0, "nonce": "r740"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-old", "generation": 1, "groups": ["rooters"], "active": True},
                    ],
                },
                {
                    "revision": 741,
                    "proof": {"revision": 741, "issued_at": 1, "nonce": "r741"},
                    "principals": [
                        {"username": "ren", "subject_id": "subj-ren-new", "generation": 2, "groups": ["readers"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 740},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ren", "resource": "cluster", "action": "admin"},
                {"op": "publish", "tick": 1, "revision": 741},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "ren", "resource": "cluster", "action": "admin"},
            ],
        }
        build_binary()
        case_dir = WORK / "poisoned"
        state_dir = case_dir / "state"
        if case_dir.exists():
            shutil.rmtree(case_dir)
        case_dir.mkdir(parents=True, exist_ok=True)
        scenario_path = case_dir / "scenario.json"
        scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
        partial_out = OUTDIR / "poisoned-partial.json"
        _run_authzctl(
            [
                "run-case",
                "--case",
                str(scenario_path),
                "--state",
                str(state_dir),
                "--out",
                str(partial_out),
                "--stop-after-step",
                "3",
            ]
        )
        corrupt_index = [
            {
                "group": "rooters",
                "members": [{"username": "ren", "subject_id": "subj-ren-old", "generation": 1}],
            }
        ]
        (state_dir / "group_index.json").write_text(json.dumps(corrupt_index, indent=2), encoding="utf-8")
        manifest = load_manifest(state_dir)
        manifest["refresh_epoch"] = 0
        (state_dir / "run_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        resume_out = OUTDIR / "poisoned-resume.json"
        _run_authzctl(
            [
                "run-case",
                "--case",
                str(scenario_path),
                "--state",
                str(state_dir),
                "--out",
                str(resume_out),
                "--resume",
            ]
        )
        resume_trace = json.loads(resume_out.read_text(encoding="utf-8"))
        after = decision(resume_trace, "ren", "cluster", "admin", 1)
        assert after["result"] == "deny", after
        assert after["subject_id"] == "subj-ren-new"
        assert ("ren", "subj-ren-old", 1) not in indexed_members(resume_trace, "rooters")
        assert normalize_index(resume_trace["group_index"]) == normalize_index(
            json.loads((state_dir / "group_index.json").read_text(encoding="utf-8"))
        )
        final_manifest = load_manifest(state_dir)
        assert final_manifest["refresh_epoch"] == 2
        assert cache_entry(resume_trace, "ren")["refresh_epoch"] == 2

    def test_group_shrink_removes_stale_group_index(self):
        """Losing a group without revocation must not leave the old group in the derived index."""
        scenario = {
            "name": "generated-group-shrink-index",
            "freshness_bound": 3,
            "resources": base_resources("ops") + [{"id": "vault", "actions": {"read": ["vault"]}}],
            "snapshots": [
                {
                    "revision": 820,
                    "proof": {"revision": 820, "issued_at": 0, "nonce": "r820"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["ops", "vault"], "active": True},
                    ],
                },
                {
                    "revision": 821,
                    "proof": {"revision": 821, "issued_at": 1, "nonce": "r821"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["vault"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 820},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 0, "username": "ava", "resource": "vault", "action": "read"},
                {"op": "publish", "tick": 1, "revision": 821},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 1, "username": "ava", "resource": "vault", "action": "read"},
            ],
        }
        trace, _, state_dir, _ = run_case("shrink", scenario)
        assert decision(trace, "ava", "resource", "use", 0)["result"] == "allow"
        assert decision(trace, "ava", "vault", "read", 0)["result"] == "allow"
        denied = decision(trace, "ava", "resource", "use", 1)
        assert denied["result"] == "deny", denied
        assert decision(trace, "ava", "vault", "read", 1)["result"] == "allow"
        assert ("ava", "ava-1", 1) not in indexed_members(trace, "ops")
        assert ("ava", "ava-1", 1) in indexed_members(trace, "vault")
        entry = cache_entry(trace, "ava")
        assert entry["refresh_epoch"] == 2
        assert entry["groups"] == ["vault"]
        disk_index = json.loads((state_dir / "group_index.json").read_text(encoding="utf-8"))
        assert normalize_index(trace["group_index"]) == normalize_index(disk_index)

    def test_revocation_chain_keeps_disk_surfaces_coherent(self):
        """A multi-step revocation chain must leave persisted cache and index aligned with the trace."""
        scenario = {
            "name": "generated-revocation-chain",
            "freshness_bound": 2,
            "resources": base_resources("ops") + [{"id": "desk", "actions": {"open": ["staff"]}}],
            "snapshots": [
                {
                    "revision": 810,
                    "proof": {"revision": 810, "issued_at": 0, "nonce": "r810"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": ["ops"], "active": True},
                        {"username": "bo", "subject_id": "bo-1", "generation": 1, "groups": ["staff"], "active": True},
                    ],
                },
                {
                    "revision": 811,
                    "proof": {"revision": 811, "issued_at": 1, "nonce": "r811"},
                    "principals": [
                        {"username": "ava", "subject_id": "ava-1", "generation": 1, "groups": [], "active": False},
                        {"username": "bo", "subject_id": "bo-1", "generation": 1, "groups": ["staff"], "active": True},
                    ],
                },
            ],
            "steps": [
                {"op": "publish", "tick": 0, "revision": 810},
                {"op": "refresh", "tick": 0},
                {"op": "authorize", "tick": 0, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "publish", "tick": 1, "revision": 811},
                {"op": "refresh", "tick": 1},
                {"op": "authorize", "tick": 1, "username": "ava", "resource": "resource", "action": "use"},
                {"op": "authorize", "tick": 1, "username": "bo", "resource": "desk", "action": "open"},
            ],
        }
        trace, _, state_dir, _ = run_case("chain", scenario)
        assert decision(trace, "ava", "resource", "use", 0)["result"] == "allow"
        assert decision(trace, "ava", "resource", "use", 1)["result"] == "deny"
        assert decision(trace, "bo", "desk", "open", 1)["result"] == "allow"
        ava_entry = cache_entry(trace, "ava")
        assert ava_entry["revoked"] is True
        assert ava_entry["groups"] == []
        assert ava_entry["refresh_epoch"] == 2
        persisted_cache = json.loads((state_dir / "cache_entries.json").read_text(encoding="utf-8"))
        persisted_index = json.loads((state_dir / "group_index.json").read_text(encoding="utf-8"))
        assert normalize_entries(trace["cache_entries"]) == normalize_entries(persisted_cache)
        assert normalize_index(trace["group_index"]) == normalize_index(persisted_index)
        journal_lines = (state_dir / "refresh_journal.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(journal_lines) == 2
