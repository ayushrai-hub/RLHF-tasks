"""Checks for the Rookline tournament appeal proof contract."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

APP = Path(os.environ.get("TASK_APP_DIR", "/app"))
ENV = APP / "environment"
BIN = APP / "bin" / "rookline"
OUT = APP / "output" / "tournament-appeal-proof.json"


def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def fnv1a64(raw: bytes) -> str:
    value = 0xCBF29CE484222325
    for byte in raw:
        value ^= byte
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"fnv1a64:{value:016x}"


def sig(fmt: str, match_id: str, home: str, away: str, epoch: int, home_key: str, away_key: str) -> str:
    prefix = "SIG" if fmt == "v2" else "LEGACY"
    return f"{prefix}:{match_id}:{home}:{away}:{epoch}:{home_key}:{away_key}"


def build_binary() -> None:
    (APP / "bin").mkdir(parents=True, exist_ok=True)
    _run(["cargo", "build", "--quiet", "--release"], cwd=ENV)
    shutil.copy2(ENV / "target" / "release" / "rookline", BIN)


def prove(case_text: str, name: str) -> dict:
    build_binary()
    root = Path(tempfile.mkdtemp(prefix=f"rookline-{name}-"))
    case_path = root / f"{name}.rtl"
    out_path = root / f"{name}.json"
    normalized = textwrap.dedent(case_text).strip() + "\n"
    case_path.write_text(normalized, encoding="utf-8")
    _run([str(BIN), "prove", "--cases", str(case_path), "--out", str(out_path)], cwd=ENV)
    doc = json.loads(out_path.read_text(encoding="utf-8"))
    assert doc["source_fingerprint"] == fnv1a64(normalized.encode("utf-8"))
    return doc


def assert_case_judge(case: dict) -> None:
    judge = case["judge"]
    assert isinstance(judge["verdict"], str)
    assert isinstance(judge["errors"], list)
    accepted = sum(
        1
        for match in case["matches"]
        if match["status"] in {"accepted", "replay_accepted"}
    )
    assert judge["accepted_match_count"] == accepted


def first_case(doc: dict) -> dict:
    assert doc["schema"] == "rookline.tournament-appeal-proof.v1"
    assert doc["generated_by"] == "rookline prove"
    assert doc["case_count"] == len(doc["cases"])
    case = doc["cases"][0]
    assert_case_judge(case)
    return case


def by_id(entries: list[dict]) -> dict[str, dict]:
    return {entry["id"]: entry for entry in entries}


def standings_by_player(case: dict) -> dict[str, dict]:
    return {entry["player"]: entry for entry in case["standings"]}


class TestRooklineAppealProof:
    def test_public_workflow_regenerates_schema_and_provenance(self) -> None:
        """The public workflow overwrites stale proof content and reports the documented schema."""
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text('{"schema":"tampered"}\n', encoding="utf-8")
        env = os.environ.copy()
        env["TASK_APP_DIR"] = str(APP)
        subprocess.run(["bash", str(ENV / "scripts" / "run_public_cases.sh")], cwd=ENV, env=env, check=True)
        proof_text = OUT.read_text(encoding="utf-8")
        proof_doc = json.loads(proof_text)
        public_raw = (ENV / "fixtures" / "public_cases.rtl").read_bytes()
        assert proof_doc["schema"] == "rookline.tournament-appeal-proof.v1"
        assert proof_doc["generated_by"] == "rookline prove"
        assert proof_doc["source_fingerprint"] == fnv1a64(public_raw)
        assert proof_doc["case_count"] == 1
        assert "tampered" not in proof_text
        assert_case_judge(proof_doc["cases"][0])

    def test_replay_epoch_controls_revocation_after_appeal(self) -> None:
        """A replay after revocation is rejected even when the original signed match predates revocation."""
        doc = prove(
            f"""
            case revoked-replay
            player Ada key=oak registered=1 revoked=30
            player Bea key=elm registered=1 revoked=none
            match m1 epoch=10 format=v2 home=Ada away=Bea sig={sig('v2', 'm1', 'Ada', 'Bea', 10, 'oak', 'elm')} declared=home moves=H2[clean],A1[tempo],H1[appeal]
            appeal ap1 target=m1 epoch=20 replay_epoch=40 sig={sig('v2', 'm1', 'Ada', 'Bea', 40, 'oak', 'elm')} declared=home moves=H2[appeal],A1[clean],H1[tempo]
            endcase
            """,
            "revoked-replay",
        )
        case = first_case(doc)
        match = by_id(case["matches"])["m1"]
        assert match["status"] == "replay_rejected"
        assert match["winner"] is None
        assert "revoked_at_replay_epoch:Ada" in match["errors"]
        table = standings_by_player(case)
        assert table["Ada"] == {"player": "Ada", "wins": 0, "losses": 0, "draws": 0, "points": 0}
        assert table["Bea"] == {"player": "Bea", "wins": 0, "losses": 0, "draws": 0, "points": 0}
        assert case["appeals"][0]["status"] == "replay_rejected"

    def test_annotation_extensions_are_not_legal_aliases(self) -> None:
        """Hyphenated annotation extensions are rejected instead of being scored as appeal moves."""
        doc = prove(
            f"""
            case illegal-annotation
            player Cy key=ivy registered=1 revoked=none
            player Di key=jun registered=1 revoked=none
            match m2 epoch=12 format=v2 home=Cy away=Di sig={sig('v2', 'm2', 'Cy', 'Di', 12, 'ivy', 'jun')} declared=home moves=H2[appeal-waiver],A1[clean],H1[tempo]
            endcase
            """,
            "illegal-annotation",
        )
        case = first_case(doc)
        match = by_id(case["matches"])["m2"]
        assert match["status"] == "rejected"
        assert match["winner"] is None
        assert "illegal_annotation:appeal-waiver" in match["errors"]
        trace = match["move_trace"][0]
        assert trace["legal"] is False
        assert trace["reason"] == "illegal_annotation:appeal-waiver"
        table = standings_by_player(case)
        assert table["Cy"]["points"] == 0
        assert table["Di"]["points"] == 0

    def test_legacy_signed_records_before_revocation_remain_authoritative(self) -> None:
        """A valid v1 record before revocation still contributes to standings."""
        doc = prove(
            f"""
            case legacy-before-revocation
            player Eli key=koa registered=1 revoked=50
            player Fox key=birch registered=1 revoked=none
            match m3 epoch=12 format=v1 home=Eli away=Fox sig={sig('v1', 'm3', 'Eli', 'Fox', 12, 'koa', 'birch')} declared=away moves=H1[legacy],A2[clean],A1[tempo]
            endcase
            """,
            "legacy-before-revocation",
        )
        case = first_case(doc)
        match = by_id(case["matches"])["m3"]
        assert match["status"] == "accepted"
        assert match["winner"] == "Fox"
        table = standings_by_player(case)
        assert table["Fox"]["wins"] == 1
        assert table["Fox"]["points"] == 3
        assert table["Eli"]["losses"] == 1

    def test_replay_before_future_revocation_still_scores(self) -> None:
        """The replay epoch rule does not reject players whose revocation happens later."""
        doc = prove(
            f"""
            case replay-before-future-revocation
            player Gia key=cedar registered=1 revoked=80
            player Hal key=spruce registered=1 revoked=none
            match m4 epoch=10 format=v2 home=Gia away=Hal sig={sig('v2', 'm4', 'Gia', 'Hal', 10, 'cedar', 'spruce')} declared=away moves=H1[clean],A2[tempo]
            appeal ap4 target=m4 epoch=22 replay_epoch=40 sig={sig('v2', 'm4', 'Gia', 'Hal', 40, 'cedar', 'spruce')} declared=home moves=H2[appeal],A1[clean],H1[tempo]
            endcase
            """,
            "replay-before-future-revocation",
        )
        case = first_case(doc)
        match = by_id(case["matches"])["m4"]
        assert match["status"] == "replay_accepted"
        assert match["epoch_used"] == 40
        assert match["winner"] == "Gia"
        table = standings_by_player(case)
        assert table["Gia"]["wins"] == 1
        assert table["Gia"]["points"] == 3
        assert table["Hal"]["losses"] == 1

    def test_direct_output_rewrite_does_not_survive_regeneration(self) -> None:
        """Changing the proof file alone is undone by a fresh workflow run."""
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text('{"schema":"rookline.tournament-appeal-proof.v1","case_count":999}\n', encoding="utf-8")
        env = os.environ.copy()
        env["TASK_APP_DIR"] = str(APP)
        subprocess.run(["bash", str(ENV / "scripts" / "run_public_cases.sh")], cwd=ENV, env=env, check=True)
        proof_doc = json.loads(OUT.read_text(encoding="utf-8"))
        assert proof_doc["case_count"] == 1
        public_case = first_case(proof_doc)
        public_matches = by_id(public_case["matches"])
        assert public_matches["m_alpha_beta"]["status"] == "replay_rejected"
        assert public_matches["m_beta_cato"]["status"] == "rejected"
        assert public_matches["m_legacy"]["status"] == "accepted"

    def test_standings_break_equal_points_by_wins(self) -> None:
        """Players with equal points are ordered by win count before player id."""
        doc = prove(
            f"""
            case wins-tiebreak
            player Drawna key=dawn registered=1 revoked=none
            player Winny key=win registered=1 revoked=none
            player Pax key=pax registered=1 revoked=none
            player Quin key=quin registered=1 revoked=none
            player Rex key=rex registered=1 revoked=none
            match m1 epoch=10 format=v2 home=Winny away=Pax sig={sig('v2', 'm1', 'Winny', 'Pax', 10, 'win', 'pax')} declared=home moves=H2[clean],A1[tempo],H1[appeal]
            match m2 epoch=11 format=v2 home=Drawna away=Quin sig={sig('v2', 'm2', 'Drawna', 'Quin', 11, 'dawn', 'quin')} declared=draw moves=H1[clean],A1[tempo]
            match m3 epoch=12 format=v2 home=Drawna away=Pax sig={sig('v2', 'm3', 'Drawna', 'Pax', 12, 'dawn', 'pax')} declared=draw moves=H1[clean],A1[tempo]
            match m4 epoch=13 format=v2 home=Drawna away=Rex sig={sig('v2', 'm4', 'Drawna', 'Rex', 13, 'dawn', 'rex')} declared=draw moves=H1[clean],A1[tempo]
            endcase
            """,
            "wins-tiebreak",
        )
        case = first_case(doc)
        table = standings_by_player(case)
        assert table["Winny"]["points"] == 3
        assert table["Winny"]["wins"] == 1
        assert table["Drawna"]["points"] == 3
        assert table["Drawna"]["wins"] == 0
        ordered = [entry["player"] for entry in case["standings"]]
        assert ordered.index("Winny") < ordered.index("Drawna")

    def test_source_fingerprint_changes_with_case_authority(self) -> None:
        """Different local record authorities produce different proof fingerprints."""
        doc_a = prove(
            f"""
            case digest-a
            player Ira key=maple registered=1 revoked=none
            player Jo key=poplar registered=1 revoked=none
            match ma epoch=9 format=v2 home=Ira away=Jo sig={sig('v2', 'ma', 'Ira', 'Jo', 9, 'maple', 'poplar')} declared=home moves=H2[clean],A1[tempo]
            endcase
            """,
            "digest-a",
        )
        doc_b = prove(
            f"""
            case digest-b
            player Ira key=maple registered=1 revoked=none
            player Jo key=poplar registered=1 revoked=none
            match mb epoch=9 format=v2 home=Ira away=Jo sig={sig('v2', 'mb', 'Ira', 'Jo', 9, 'maple', 'poplar')} declared=draw moves=H1[clean],A1[tempo]
            endcase
            """,
            "digest-b",
        )
        assert doc_a["source_fingerprint"] != doc_b["source_fingerprint"]
        assert first_case(doc_a)["standings"][0]["player"] == "Ira"
        assert first_case(doc_b)["standings"][0]["draws"] == 1
