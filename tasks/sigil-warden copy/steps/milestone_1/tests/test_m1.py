"""Milestone 1: the warden `verify` subcommand.

Each test drives the agent's /app/warden binary as a black box and checks that it
authorizes or rejects exactly as /app/SPEC.md requires. Expected values are computed
independently from the spec; the binary is never trusted to grade itself.
"""
import glob
import json
import os
import subprocess
from pathlib import Path

WARDEN = os.environ.get("WARDEN_BIN", "/app/warden")
HERE = Path(__file__).resolve().parent
NAMED = json.loads((HERE / "named_m1.json").read_text())


def _build_if_needed():
    """Best-effort: if the agent left Go source but no binary, build it (offline, stdlib)."""
    if os.path.exists(WARDEN) and os.access(WARDEN, os.X_OK):
        return
    if WARDEN != "/app/warden":
        return
    env = dict(os.environ, GOTOOLCHAIN="local", GOFLAGS="-mod=mod")
    if os.path.exists("/app/warden.go"):
        r = subprocess.run(["go", "build", "-o", WARDEN, "/app/warden.go"],
                           cwd="/app", env=env, capture_output=True, text=True)
        if r.returncode == 0:
            return
    if glob.glob("/app/*.go"):
        if not os.path.exists("/app/go.mod"):
            subprocess.run(["go", "mod", "init", "warden"], cwd="/app", env=env,
                           capture_output=True, text=True)
        subprocess.run(["go", "build", "-o", WARDEN, "."], cwd="/app", env=env,
                       capture_output=True, text=True)


def run_verify(case):
    args = [WARDEN, "verify", "--key", case["key"]]
    for flag in ("now", "path", "method", "ip"):
        if case.get(flag) is not None:
            args += ["--" + flag, str(case[flag])]
    args.append(case["token"])
    p = subprocess.run(args, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr


def check(case):
    rc, out, _ = run_verify(case)
    if case["rc"] == 0:
        assert rc == 0, f"expected authorized, got rc={rc} for {case['token']}"
        assert out == f"OK {case['scope']}", f"wrong scope line: {out!r}"
    else:
        assert rc != 0, f"expected rejection, got rc=0 ({out!r}) for {case['token']}"


class TestMilestone1:
    def setup_method(self):
        """Ensure a warden binary is available before each test."""
        _build_if_needed()

    def test_binary_exists(self):
        """The agent must deliver an executable checker at /app/warden."""
        assert os.path.exists(WARDEN) and os.access(WARDEN, os.X_OK), "/app/warden missing"

    def test_no_caveats_grants_root(self):
        """A token with no caveats authorizes any request and reports scope '/'."""
        check(NAMED["no_caveats_grants_root"])

    def test_path_segment_containment(self):
        """`path` matches by whole path segments, not string prefix."""
        check(NAMED["path_allows_subtree"])
        check(NAMED["path_segment_subtree_ok"])
        check(NAMED["path_denies_sibling"])
        check(NAMED["path_is_segmentwise_not_string_prefix"])

    def test_exp_is_strict_upper_bound(self):
        """`exp` authorizes only while now < exp; now == exp is rejected."""
        check(NAMED["exp_allows_earlier_now"])
        check(NAMED["exp_excludes_equal_now"])

    def test_nbf_is_inclusive_lower_bound(self):
        """`nbf` authorizes once now >= nbf; now == nbf is allowed."""
        check(NAMED["nbf_includes_equal_now"])
        check(NAMED["nbf_excludes_earlier_now"])

    def test_unknown_caveat_fails_closed(self):
        """An unrecognized caveat type must cause rejection, never silent acceptance."""
        check(NAMED["unknown_caveat_type_fails_closed"])

    def test_method_set_membership(self):
        """`method` membership is case-insensitive over the comma-separated set."""
        check(NAMED["method_membership_case_insensitive"])
        check(NAMED["method_not_in_set"])

    def test_repeated_caveats_intersect(self):
        """Repeated caveats of one type must all hold (restrictions only narrow)."""
        check(NAMED["repeated_method_intersects"])
        check(NAMED["repeated_method_intersects_ok"])

    def test_cidr_membership(self):
        """`cidr` authorizes only client IPs inside the block."""
        check(NAMED["cidr_inside"])
        check(NAMED["cidr_outside"])

    def test_nested_paths_report_deepest_scope(self):
        """Effective scope is the path caveat with the most segments."""
        check(NAMED["nested_paths_report_deepest_scope"])

    def test_missing_context_fails_closed(self):
        """A caveat whose context field was not supplied does not hold."""
        check(NAMED["caveat_without_context_fails_closed"])

    def test_signature_integrity(self):
        """Tampering with the tag or with a caveat after signing is rejected."""
        check(NAMED["tampered_tag_rejected"])
        check(NAMED["swapped_caveat_rejected"])

    def test_malformed_token_rejected(self):
        """A structurally invalid token is rejected, not crashed on."""
        check(NAMED["malformed_token_rejected"])

    def test_additional_edge_cases(self):
        """Duplicate path caveats, a malformed client IP, and an empty method entry."""
        check(NAMED["duplicate_path_scope"])
        check(NAMED["cidr_rejects_malformed_ip"])
        check(NAMED["method_trailing_comma_ignored"])

    def test_token_via_stdin(self):
        """A token argument of '-' is read from standard input."""
        c = NAMED["no_caveats_grants_root"]
        args = [WARDEN, "verify", "--key", c["key"], "--now", str(c["now"]),
                "--path", c["path"], "-"]
        p = subprocess.run(args, input=c["token"], capture_output=True, text=True)
        assert p.returncode == 0 and p.stdout.strip() == f"OK {c['scope']}", p.stdout

    def test_corpus(self):
        """Match the spec across a large randomized corpus of accept/reject cases."""
        fails = []
        with (HERE / "vectors_m1.jsonl").open() as f:
            cases = [json.loads(line) for line in f if line.strip()]
        for case in cases:
            rc, out, _ = run_verify(case)
            if case["rc"] == 0:
                ok = rc == 0 and out == f"OK {case['scope']}"
            else:
                ok = rc != 0
            if not ok:
                fails.append((case, rc, out))
                if len(fails) > 15:
                    break
        assert not fails, f"{len(fails)} corpus mismatches; first: {fails[0]}"
