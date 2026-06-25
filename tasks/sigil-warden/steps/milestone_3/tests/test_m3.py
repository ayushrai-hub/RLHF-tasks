"""Milestone 3: third-party caveats — issue, discharge, bind, and verify.

Construction is deterministic, so minting/discharging/binding are compared byte-for-byte
against the spec. Verification is additionally checked against reference-built tokens and
discharges (so the agent's checker must implement the exact spec, not merely agree with its
own minting), and end-to-end through the agent's own pipeline.
"""
import base64
import glob
import json
import os
import subprocess
from pathlib import Path

WARDEN = os.environ.get("WARDEN_BIN", "/app/warden")
HERE = Path(__file__).resolve().parent
NAMED = json.loads((HERE / "named_m3.json").read_text())
CRAFTED = json.loads((HERE / "crafted_m3.json").read_text())
KX = "00112233445566778899aabbccddeeff"
TPKX = "0f1e2d3c4b5a69788796a5b4c3d2e1f0"


def _build_if_needed():
    if os.path.exists(WARDEN) and os.access(WARDEN, os.X_OK):
        return
    if WARDEN != "/app/warden":
        return
    env = dict(os.environ, GOTOOLCHAIN="local", GOFLAGS="-mod=mod")
    if os.path.exists("/app/warden.go"):
        if subprocess.run(["go", "build", "-o", WARDEN, "/app/warden.go"], cwd="/app",
                          env=env, capture_output=True, text=True).returncode == 0:
            return
    if glob.glob("/app/*.go"):
        if not os.path.exists("/app/go.mod"):
            subprocess.run(["go", "mod", "init", "warden"], cwd="/app", env=env, capture_output=True, text=True)
        subprocess.run(["go", "build", "-o", WARDEN, "."], cwd="/app", env=env, capture_output=True, text=True)


def run(args, want_zero=True):
    p = subprocess.run([WARDEN] + args, capture_output=True, text=True)
    if want_zero:
        assert p.returncode == 0, f"warden {args[0]} failed rc={p.returncode}: {p.stderr}"
    return p.returncode, p.stdout.strip(), p.stderr


def b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def extract_cid(token):
    for part in token.split(".")[2].split("~"):
        raw = b64d(part)
        if raw.startswith(b"third="):
            return raw.decode().split("|")[2]
    raise AssertionError("token has no third-party caveat")


def do_verify(case):
    args = ["verify", "--key", case["key"]]
    for flag in ("now", "path", "method", "ip"):
        if case.get(flag) is not None:
            args += ["--" + flag, str(case[flag])]
    for d in case.get("discharges", []):
        args += ["--discharge", d]
    args.append(case["token"])
    rc, out, _ = run(args, want_zero=False)
    if case["rc"] == 0:
        assert rc == 0 and out == f"OK {case['scope']}", f"{case.get('name','?')}: {rc} {out!r}"
    else:
        assert rc != 0, f"{case.get('name','?')}: expected reject, got {out!r}"


class TestMilestone3:
    def setup_method(self):
        """Ensure a warden binary is available before each test."""
        _build_if_needed()

    def test_mint_third_matches_spec(self):
        """Minting a token carrying a third-party caveat yields the spec's exact bytes."""
        c = NAMED["mint_third"]
        args = ["mint", "--key", c["key"], "--id", c["id"]]
        for f in c["firsts"]:
            args += ["--caveat", f]
        args += ["--third", c["third"]]
        assert run(args)[1] == c["expect"]

    def test_discharge_matches_spec(self):
        """A discharge sigil for a recovered caveat key matches the spec's exact bytes."""
        c = NAMED["discharge"]
        args = ["discharge", "--tpkey", c["tpkey"], "--predicate", c["predicate"], "--cid", c["cid"]]
        for cav in c["caveats"]:
            args += ["--caveat", cav]
        assert run(args)[1] == c["expect"]

    def test_bind_matches_spec(self):
        """Binding a discharge to a root token matches the spec's exact bytes."""
        c = NAMED["bind"]
        assert run(["bind", c["root"], c["disch"]])[1] == c["expect"]

    def test_crafted_vectors(self):
        """Verify reference-built tokens: a valid bound discharge is accepted; missing,
        unbound, expired, wrong-key, mis-bound, and tampered cases are rejected."""
        for case in CRAFTED:
            do_verify(case)

    def test_end_to_end_pipeline(self):
        """The agent's own mint, discharge, bind, and verify compose correctly and the
        discharge requirement and binding are actually enforced."""
        root = run(["mint", "--key", KX, "--id", "user42", "--caveat", "path=/reports",
                    "--third", f"auth|user=alice|{TPKX}"])[1]
        cid = extract_cid(root)
        disch = run(["discharge", "--tpkey", TPKX, "--predicate", "user=alice",
                     "--cid", cid, "--caveat", "exp=2000000000"])[1]
        bound = run(["bind", root, disch])[1]
        base = ["verify", "--key", KX, "--now", "1700000000", "--path", "/reports/x"]
        rc, out, _ = run(base + ["--discharge", bound, root], want_zero=False)
        assert rc == 0 and out == "OK /reports", out
        assert run(base + [root], want_zero=False)[0] != 0, "missing discharge accepted"
        assert run(base + ["--discharge", disch, root], want_zero=False)[0] != 0, "unbound discharge accepted"

    def test_fuzz_corpus(self):
        """Match the spec across a randomized corpus of third-party verify scenarios."""
        fails = []
        with (HERE / "vectors_m3.jsonl").open() as f:
            for line in f:
                if not line.strip():
                    continue
                case = json.loads(line)
                args = ["verify", "--key", case["key"]]
                for flag in ("now", "path", "method", "ip"):
                    if case.get(flag) is not None:
                        args += ["--" + flag, str(case[flag])]
                for d in case.get("discharges", []):
                    args += ["--discharge", d]
                args.append(case["token"])
                rc, out, _ = run(args, want_zero=False)
                ok = (rc == 0 and out == f"OK {case['scope']}") if case["rc"] == 0 else (rc != 0)
                if not ok:
                    fails.append((case.get("token", "")[:40], rc, out))
                    if len(fails) > 12:
                        break
        assert not fails, f"{len(fails)} third-party corpus mismatches; first: {fails[0]}"
