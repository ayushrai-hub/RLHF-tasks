import gzip
import json
import os
import subprocess
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", "/workspace"))
CMD = ["go", "run", str(WORKSPACE / "cmd/claimtower")]


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            if isinstance(row, str):
                f.write(row + "\n")
            else:
                f.write(json.dumps(row, separators=(",", ":")) + "\n")


def write_gzip_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def run_claimtower(args):
    return subprocess.run(CMD + args, cwd=WORKSPACE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def read_tsv(path: Path):
    return [line.rstrip("\n").split("\t") for line in path.read_text(encoding="utf-8").splitlines()]


def assert_pretty_json(path: Path):
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    assert raw == json.dumps(data, indent=2) + "\n"
    return data


class TestMilestone1:
    def test_ingest_aliases_gzip_duplicate_resolution_ignored_statuses_and_totals(self, tmp_path):
        """Claim ingestion handles aliases, gzip input, duplicate tie-breaks, ignored closed statuses, sorted JSON, and totals."""
        root = tmp_path / "claims"
        write_jsonl(root / "zeta" / "north.claim.jsonl", [
            {"claim_id": "CLM-001", "revision": 1, "product": "auto", "loss_date": "2026-06-01", "status": "open", "reserve": 10000, "paid": 1000, "severity": 2, "handler": "Uma", "county": "north"},
            {"id": "CLM-002", "rev": 2, "line": "property", "lossOn": "2026-05-20", "state": "Open", "reserve": 40000, "paid": 5000, "severity": 4, "handler": "Ken", "county": "west"},
            {"claim_id": "CLM-CLOSED", "revision": 8, "product": "auto", "loss_date": "2026-05-01", "status": "closed", "reserve": 1, "paid": 1, "severity": 1},
            {"claim_id": "CLM-001", "revision": 3, "product": "auto", "loss_date": "2026-05-30", "status": "OPEN", "reserve": 15000, "paid": 2000, "severity": 3, "handler": "Uma", "county": "north"},
        ])
        write_jsonl(root / "a" / "tie.claim.jsonl", [
            {"claim_id": "CLM-TIE", "revision": 7, "product": "liability", "loss_date": "2026-06-10", "status": "open", "reserve": 9000, "paid": 0, "severity": 5, "county": "central"},
        ])
        write_gzip_jsonl(root / "b" / "tie.claim.jsonl.gz", [
            {"claim_id": "CLM-TIE", "revision": 7, "product": "liability", "loss_date": "2026-06-09", "status": "open", "reserve": 99999, "paid": 1, "severity": 1, "county": "wrong"},
        ])
        claims_out = tmp_path / "nested" / "out" / "claims.json"
        issues_out = tmp_path / "nested" / "audit" / "issues.tsv"
        run_claimtower(["ingest", "--claims-root", str(root), "--as-of", "2026-06-15", "--claims-out", str(claims_out), "--issues-out", str(issues_out)])

        data = assert_pretty_json(claims_out)
        assert data["as_of"] == "2026-06-15"
        assert data["claim_count"] == 3
        assert [c["claim_id"] for c in data["claims"]] == ["CLM-001", "CLM-002", "CLM-TIE"]
        chosen = {c["claim_id"]: c for c in data["claims"]}
        assert chosen["CLM-001"]["revision"] == 3
        assert chosen["CLM-001"]["status"] == "open"
        assert chosen["CLM-001"]["age_days"] == 16
        assert chosen["CLM-TIE"]["county"] == "central"
        assert chosen["CLM-TIE"]["source_file"] == str((root / "a" / "tie.claim.jsonl").resolve())
        assert data["totals"] == {"open_claims": 3, "reserve": 64000, "paid": 7000}
        assert claims_out.read_bytes().endswith(b"\n")
        assert read_tsv(issues_out) == [["source_file", "source_line", "kind", "entity", "detail"]]

    def test_invalid_claim_rows_are_recoverable_precise_and_required_flags_fail(self, tmp_path):
        """Invalid claim rows produce sorted invalid_claim issues while valid rows still appear, and missing CLI flags fail."""
        root = tmp_path / "claims"
        bad_file = root / "bad" / "broken.claim.jsonl"
        write_jsonl(bad_file, [
            "{bad json",
            ["not", "object"],
            {"revision": 1, "product": "auto", "loss_date": "2026-06-01", "status": "open", "reserve": 1, "paid": 0, "severity": 1},
            {"claim_id": "CLM-NEG", "revision": 1, "product": "auto", "loss_date": "2026-06-01", "status": "open", "reserve": 1, "paid": -4, "severity": 1},
            {"claim_id": "CLM-SEV", "revision": 1, "product": "auto", "loss_date": "2026-06-01", "status": "open", "reserve": 1, "paid": 0, "severity": 9},
            {"claim_id": "CLM-FUT", "revision": 1, "product": "auto", "loss_date": "2026-07-01", "status": "open", "reserve": 1, "paid": 0, "severity": 1},
            {"claim_id": "CLM-OK", "revision": 1, "product": "auto", "loss_date": "2026-06-01", "status": "open", "reserve": 10, "paid": 2, "severity": 2},
        ])
        claims_out = tmp_path / "deep" / "claims.json"
        issues_out = tmp_path / "deep" / "issues.tsv"
        run_claimtower(["ingest", "--claims-root", str(root), "--as-of", "2026-06-15", "--claims-out", str(claims_out), "--issues-out", str(issues_out)])
        data = assert_pretty_json(claims_out)
        assert [c["claim_id"] for c in data["claims"]] == ["CLM-OK"]
        issue_rows = read_tsv(issues_out)
        assert issue_rows[0] == ["source_file", "source_line", "kind", "entity", "detail"]
        bodies = issue_rows[1:]
        assert all(row[0] == str(bad_file.resolve()) for row in bodies)
        assert all(row[2] == "invalid_claim" for row in bodies)
        assert {row[4] for row in bodies} >= {"bad_json", "not_object", "claim_id", "paid", "severity", "loss_date_after_as_of"}
        issue_by_line = {int(row[1]): row for row in bodies}
        assert issue_by_line[1][2:] == ["invalid_claim", "", "bad_json"]
        assert issue_by_line[2][2:] == ["invalid_claim", "", "not_object"]
        assert issue_by_line[3][2:] == ["invalid_claim", "", "claim_id"]
        assert issue_by_line[4][2:] == ["invalid_claim", "CLM-NEG", "paid"]
        assert issue_by_line[5][2:] == ["invalid_claim", "CLM-SEV", "severity"]
        assert issue_by_line[6][2:] == ["invalid_claim", "CLM-FUT", "loss_date_after_as_of"]
        assert [int(row[1]) for row in bodies] == sorted(int(row[1]) for row in bodies)
        assert issues_out.read_bytes().endswith(b"\n")

        missing = subprocess.run(CMD + ["ingest", "--claims-root", str(root)], cwd=WORKSPACE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert missing.returncode != 0
