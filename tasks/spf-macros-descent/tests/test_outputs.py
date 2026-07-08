"""Behavioural tests for the spf-trace evaluator.

The oracle writes /app/output/verdicts.ndjson and /app/output/summary.json.
These tests cover pinned verdicts, summary counts, budget behaviour, macro
handling, cross-cycle traps (memoization, redirect loop, include depth), IPv4-
mapped IPv6 family rules, multiple-v=spf1 permerror, the exact mechanism field
grammar, the chain_digest binding, sample self-check, rebuild-and-append
mutation, inputs unchanged, and determinism.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

VERDICTS = Path("/app/output/verdicts.ndjson")
SUMMARY = Path("/app/output/summary.json")
DATA = Path("/app/data")
SPF_SRC = Path("/app/spf")
BINARY = Path("/app/spf-trace")


def _read_verdicts() -> list[dict]:
    """Parse the NDJSON verdicts file into an ordered list of dicts."""
    text = VERDICTS.read_text().splitlines()
    return [json.loads(line) for line in text if line.strip()]


def _by_id(rows: list[dict]) -> dict[str, dict]:
    """Index verdict rows by their id field."""
    return {r["id"]: r for r in rows}


def _expected_chain_digest(rows: list[dict]) -> str:
    """Recompute the chain digest from a verdict list per the docs."""
    acc = bytes(32)
    for r in rows:
        line6 = "|".join([
            r["id"], r["result"], r["mechanism"], r["domain"],
            str(r["lookups"]), str(r["void_lookups"]),
        ])
        acc = hashlib.sha256(acc + line6.encode("utf-8")).digest()
    return acc.hex()


def test_output_files_exist() -> None:
    """Verify /app/output/verdicts.ndjson and /app/output/summary.json were written."""
    assert VERDICTS.is_file(), "verdicts.ndjson missing"
    assert SUMMARY.is_file(), "summary.json missing"


def test_binary_exists_and_runs() -> None:
    """Verify /app/spf-trace exists and is executable."""
    assert BINARY.is_file(), "spf-trace binary missing"
    assert os.access(BINARY, os.X_OK), "spf-trace not executable"


def test_verdicts_line_count_matches_input() -> None:
    """One verdict line per input message, in input order."""
    inputs = [
        json.loads(line)
        for line in (DATA / "messages.jsonl").read_text().splitlines()
        if line.strip()
    ]
    rows = _read_verdicts()
    assert len(rows) == len(inputs)
    for row, msg in zip(rows, inputs, strict=True):
        assert row["id"] == msg["id"], f"order mismatch at {msg['id']}"


def test_verdict_result_alphabet() -> None:
    """Every verdict's result field is drawn from the seven documented labels."""
    valid = {"pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"}
    for row in _read_verdicts():
        assert row["result"] in valid, f"bad result: {row}"


def test_summary_shape_and_key_order() -> None:
    """summary.json keys appear in the documented order total, counts, chain_digest."""
    text = SUMMARY.read_text()
    total_idx = text.index('"total"')
    counts_idx = text.index('"counts"')
    digest_idx = text.index('"chain_digest"')
    assert total_idx < counts_idx < digest_idx, f"key order wrong: {text}"


def test_summary_counts_cover_all_seven_labels() -> None:
    """The counts object contains every one of the seven verdict labels even at zero."""
    obj = json.loads(SUMMARY.read_text())
    for key in ["pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"]:
        assert key in obj["counts"], f"missing counts key {key}"
        assert isinstance(obj["counts"][key], int)


def test_summary_counts_match_ndjson() -> None:
    """Summary total and counts agree with the verdicts file."""
    obj = json.loads(SUMMARY.read_text())
    rows = _read_verdicts()
    assert obj["total"] == len(rows)
    expected = {k: 0 for k in ["pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"]}
    for row in rows:
        expected[row["result"]] += 1
    assert obj["counts"] == expected


def test_summary_counts_pinned() -> None:
    """The distribution of verdict classes on the shipped 40-message fixture."""
    obj = json.loads(SUMMARY.read_text())
    assert obj["counts"] == {
        "pass": 19,
        "fail": 9,
        "softfail": 4,
        "neutral": 1,
        "none": 2,
        "permerror": 5,
        "temperror": 0,
    }


def test_chain_digest_matches_verdicts() -> None:
    """The chain_digest in summary.json is the sha256 chain over the six per-line fields."""
    obj = json.loads(SUMMARY.read_text())
    expected = _expected_chain_digest(_read_verdicts())
    assert obj["chain_digest"] == expected, (
        f"chain_digest mismatch: got {obj['chain_digest']}, expected {expected}"
    )


def test_simple_ip4_and_a_match() -> None:
    """Sender-a matches its a mechanism at 192.0.2.5 (m001)."""
    v = _by_id(_read_verdicts())["m001"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+a"


def test_mx_match_via_first_exchanger() -> None:
    """Sender-a matches its mx mechanism when from_ip is an mx target (m002)."""
    v = _by_id(_read_verdicts())["m002"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+mx"


def test_include_pass_only_propagation() -> None:
    """A ~all include produces softfail, which does NOT count as an include match (m004)."""
    v = _by_id(_read_verdicts())["m004"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+ip4:198.51.100.0/24"


def test_include_softfail_falls_through_to_all() -> None:
    """When include returns softfail and no later mechanism matches, -all fires (m005)."""
    v = _by_id(_read_verdicts())["m005"]
    assert v["result"] == "fail"
    assert v["mechanism"] == "-all"


def test_ipv6_include_match() -> None:
    """IPv6 addresses match ip6 CIDR inside an included policy (m006)."""
    v = _by_id(_read_verdicts())["m006"]
    assert v["result"] == "pass"


def test_redirect_mechanism_field_uses_target_not_inner() -> None:
    """A redirect-resolved verdict writes 'redirect=<target>' as mechanism, not the inner match (m007)."""
    v = _by_id(_read_verdicts())["m007"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "redirect=_spf.shared.test"


def test_redirect_ignored_when_all_present() -> None:
    """A record with a matching -all mechanism does NOT consult its redirect target (m010)."""
    v = _by_id(_read_verdicts())["m010"]
    assert v["result"] == "fail"
    assert v["mechanism"] == "-all"


def test_deep_include_chain_within_budget() -> None:
    """Sender-d chains through five nested includes and matches deep-e at m012."""
    v = _by_id(_read_verdicts())["m012"]
    assert v["result"] == "pass"
    assert v["lookups"] <= 10


def test_lookup_budget_permerror() -> None:
    """Chain of 10 nested includes exceeds max_lookups=10 -> permerror (m013)."""
    v = _by_id(_read_verdicts())["m013"]
    assert v["result"] == "permerror"
    assert v["lookups"] == 11


def test_global_void_budget_across_includes() -> None:
    """Three void lookups spread across three includes overflow max_void_lookups=2 (m014)."""
    v = _by_id(_read_verdicts())["m014"]
    assert v["result"] == "permerror"
    assert v["void_lookups"] == 3


def test_ipv4_exists_reverse_macro_mechanism_stays_unexpanded() -> None:
    """%{ir} on an IPv4 envelope matches AND the mechanism field keeps the literal macro (m015)."""
    v = _by_id(_read_verdicts())["m015"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+exists:%{ir}.rbl.example.test"


def test_ipv6_exists_reverse_macro_uses_nibble_form() -> None:
    """%{ir} on an IPv6 envelope expands to 32 nibbles before reversing (m017)."""
    v = _by_id(_read_verdicts())["m017"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+exists:%{ir}.v6rbl.example.test"


def test_qualifiers_soft_and_neutral() -> None:
    """? qualifier on all produces neutral (m021); ~ produces softfail (m023)."""
    rows = _by_id(_read_verdicts())
    assert rows["m021"]["result"] == "neutral"
    assert rows["m021"]["mechanism"] == "?all"
    assert rows["m023"]["result"] == "softfail"
    assert rows["m023"]["mechanism"] == "~all"


def test_none_verdict_when_no_spf_record() -> None:
    """A domain whose TXT records contain nothing starting with v=spf1 returns none (m028)."""
    rows = _by_id(_read_verdicts())
    assert rows["m028"]["result"] == "none"
    assert rows["m029"]["result"] == "none"


def test_a_with_cidr_length() -> None:
    """The a/24 form widens the A record match to a subnet (m025)."""
    v = _by_id(_read_verdicts())["m025"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+a/24"


def test_mx_with_cidr_length() -> None:
    """The mx/29 form widens each exchanger's A record to a subnet (m027)."""
    v = _by_id(_read_verdicts())["m027"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+mx/29"


def test_custom_delimiter_macro_local_part() -> None:
    """%{l+_} splits the local part on + or _ before rejoining with . (m031)."""
    v = _by_id(_read_verdicts())["m031"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+exists:%{l+_}.bounce.example.test"


def test_custom_delimiter_no_match_falls_to_softfail() -> None:
    """A message whose custom-delim expansion misses returns softfail via ~all (m032)."""
    v = _by_id(_read_verdicts())["m032"]
    assert v["result"] == "softfail"


def test_custom_delimiter_macro_current_domain() -> None:
    """%{d-} splits the evaluating domain on hyphen and rejoins with dot (m033)."""
    v = _by_id(_read_verdicts())["m033"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+exists:%{d-}.plus.example.test"


def test_multiple_v_spf1_records_permerror() -> None:
    """A TXT rrset with two entries starting v=spf1 is permerror per RFC 7208 §4.5 (m034)."""
    v = _by_id(_read_verdicts())["m034"]
    assert v["result"] == "permerror"
    assert v["mechanism"] == ""


def test_in_eval_lookup_memoization() -> None:
    """Duplicate include:X in one record uses the in-eval memo so lookups do not double-count (m035).

    Without memoization the same target A lookup would fire twice, pushing lookups to 5.
    """
    v = _by_id(_read_verdicts())["m035"]
    assert v["result"] == "fail"
    assert v["lookups"] == 3


def test_redirect_loop_guard() -> None:
    """sender-u redirects to sender-v which redirects to sender-u -> permerror (m036)."""
    v = _by_id(_read_verdicts())["m036"]
    assert v["result"] == "permerror"
    assert v["mechanism"] == ""


def test_include_depth_guard() -> None:
    """A self-referential include cycle hits max_redirect_hops before the lookup budget (m037).

    Because lookups are memoized, the numeric lookup budget never trips -- the depth guard is
    what stops the recursion. The final lookups counter stays small.
    """
    v = _by_id(_read_verdicts())["m037"]
    assert v["result"] == "permerror"
    assert v["lookups"] <= 5


def test_ipv4_mapped_ipv6_matches_ip4_mechanism() -> None:
    """::ffff:192.0.2.55 hits the ip4:192.0.2.55 mechanism (m038)."""
    v = _by_id(_read_verdicts())["m038"]
    assert v["result"] == "pass"
    assert v["mechanism"] == "+ip4:192.0.2.55"


def test_ipv4_mapped_ipv6_does_not_match_ip6_mechanism() -> None:
    """::ffff:192.0.2.55 is treated as IPv4 so an ip6:CIDR record does not match (m040)."""
    v = _by_id(_read_verdicts())["m040"]
    assert v["result"] == "fail"


def test_sample_selfcheck_matches_shipped_expected() -> None:
    """Running the built binary on sample_in.jsonl reproduces sample_out.ndjson byte for byte."""
    workdir = Path("/tmp/spfselfcheck")
    if workdir.exists():
        shutil.rmtree(workdir)
    (workdir / "data").mkdir(parents=True)
    (workdir / "output").mkdir()
    shutil.copy(DATA / "sample_in.jsonl", workdir / "data" / "messages.jsonl")
    shutil.copy(DATA / "dns.json", workdir / "data" / "dns.json")
    shutil.copy(DATA / "policy.json", workdir / "data" / "policy.json")
    env = os.environ.copy()
    env["SPF_DATA_DIR"] = str(workdir / "data")
    env["SPF_OUT_DIR"] = str(workdir / "output")
    result = subprocess.run(
        [str(BINARY)], env=env, check=False, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"binary error: {result.stderr}"
    produced = (workdir / "output" / "verdicts.ndjson").read_text()
    expected = (DATA / "sample_out.ndjson").read_text()
    assert produced == expected, "sample self-check mismatch"


def test_rebuild_and_append_mutation() -> None:
    """Rebuild the agent's sources from scratch and add a new envelope; verdict updates."""
    go_files = list(SPF_SRC.glob("*.go"))
    assert go_files, "no Go source in /app/spf"
    workdir = Path("/tmp/spfmutation")
    if workdir.exists():
        shutil.rmtree(workdir)
    (workdir / "data").mkdir(parents=True)
    (workdir / "output").mkdir()
    (workdir / "src").mkdir()
    for f in SPF_SRC.iterdir():
        shutil.copy(f, workdir / "src" / f.name)
    shutil.copy(DATA / "dns.json", workdir / "data" / "dns.json")
    shutil.copy(DATA / "policy.json", workdir / "data" / "policy.json")
    orig = (DATA / "messages.jsonl").read_text()
    added = {
        "id": "mut001",
        "mail_from": "zed@sender-l.test",
        "helo": "mx.sender-l.test",
        "from_ip": "192.0.2.9",
    }
    (workdir / "data" / "messages.jsonl").write_text(orig + json.dumps(added) + "\n")
    build_bin = workdir / "spf-trace"
    build = subprocess.run(
        ["go", "build", "-o", str(build_bin), "."],
        cwd=workdir / "src",
        env={**os.environ, "GOPROXY": "off", "GOTOOLCHAIN": "local"},
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build.returncode == 0, f"rebuild failed: {build.stderr}"
    env = os.environ.copy()
    env["SPF_DATA_DIR"] = str(workdir / "data")
    env["SPF_OUT_DIR"] = str(workdir / "output")
    run = subprocess.run(
        [str(build_bin)], env=env, check=False, capture_output=True, text=True, timeout=60
    )
    assert run.returncode == 0, f"rebuild-run failed: {run.stderr}"
    lines = (workdir / "output" / "verdicts.ndjson").read_text().splitlines()
    last = json.loads(lines[-1])
    assert last["id"] == "mut001"
    assert last["result"] == "pass"
    assert last["mechanism"] == "+all"


def test_inputs_unchanged() -> None:
    """The DNS snapshot, messages fixture, policy, sample pair, and docs remain in place after the run."""
    paths = [
        DATA / "dns.json",
        DATA / "messages.jsonl",
        DATA / "policy.json",
        DATA / "sample_in.jsonl",
        DATA / "sample_out.ndjson",
        Path("/app/docs/sender_macros.md"),
        Path("/app/docs/budget_limits.md"),
        Path("/app/docs/chain_digest.md"),
    ]
    for p in paths:
        assert p.exists() and p.stat().st_size > 0, f"input truncated or removed: {p}"


def test_output_deterministic() -> None:
    """Running the binary twice against the same inputs produces byte-identical outputs."""
    first_v = VERDICTS.read_bytes()
    first_s = SUMMARY.read_bytes()
    result = subprocess.run(
        [str(BINARY)], check=False, capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"rerun failed: {result.stderr}"
    second_v = VERDICTS.read_bytes()
    second_s = SUMMARY.read_bytes()
    assert first_v == second_v, "verdicts.ndjson not deterministic"
    assert first_s == second_s, "summary.json not deterministic"
