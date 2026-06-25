"""Milestone 2: the warden `mint` and `attenuate` subcommands.

Minting and attenuation are deterministic given the spec, so each emitted token is
compared byte-for-byte against the value the spec dictates. Attenuation is always invoked
without the root key, to prove the delegation property holds.
"""
import glob
import json
import os
import subprocess
from pathlib import Path

WARDEN = os.environ.get("WARDEN_BIN", "/app/warden")
HERE = Path(__file__).resolve().parent
NAMED = json.loads((HERE / "named_m2.json").read_text())


def _build_if_needed():
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


def run(args, want_zero=True):
    p = subprocess.run([WARDEN] + args, capture_output=True, text=True)
    if want_zero:
        assert p.returncode == 0, f"warden {args[0]} failed rc={p.returncode}: {p.stderr}"
    return p.returncode, p.stdout.strip(), p.stderr


def mint(case):
    args = ["mint", "--key", case["key"], "--id", case["id"]]
    for c in case["caveats"]:
        args += ["--caveat", c]
    return run(args)[1]


def attenuate(base, caveats):
    # Deliberately no --key: a holder of only the token must be able to attenuate it.
    args = ["attenuate"]
    for c in caveats:
        args += ["--caveat", c]
    args.append(base)
    return run(args)[1]


def verify(key, token, ctx):
    args = ["verify", "--key", key]
    for flag in ("now", "path", "method", "ip"):
        if ctx.get(flag) is not None:
            args += ["--" + flag, str(ctx[flag])]
    args.append(token)
    return run(args, want_zero=False)


class TestMilestone2:
    def setup_method(self):
        """Ensure a warden binary is available before each test."""
        _build_if_needed()

    def test_binary_exists(self):
        """The /app/warden binary must be present and executable."""
        assert os.path.exists(WARDEN) and os.access(WARDEN, os.X_OK), "/app/warden missing"

    def test_mint_matches_spec(self):
        """A minted token equals the canonical encoding the spec defines, byte for byte."""
        assert mint(NAMED["mint_basic"]) == NAMED["mint_basic"]["expect"]
        assert mint(NAMED["mint_no_caveats"]) == NAMED["mint_no_caveats"]["expect"]

    def test_attenuate_appends_without_key(self):
        """Attenuation, given only the token, appends caveats and yields the spec's token."""
        c = NAMED["attenuate_appends"]
        assert attenuate(c["base"], c["caveats"]) == c["expect"]
        c = NAMED["attenuate_multiple"]
        assert attenuate(c["base"], c["caveats"]) == c["expect"]

    def test_attenuated_token_enforces_new_caveat(self):
        """An attenuated token still verifies but now rejects what the new caveat forbids."""
        c = NAMED["attenuate_then_expired"]
        tok = attenuate(c["base"], c["add"])
        rc, _, _ = verify(c["key"], tok, c["verify_ctx"])
        assert rc != 0, "expired caveat added by attenuation was not enforced"

    def test_attenuated_token_still_authorizes_when_allowed(self):
        """Attenuation that does not forbid the request leaves it authorized."""
        c = NAMED["attenuate_then_ok"]
        tok = attenuate(c["base"], c["add"])
        rc, out, _ = verify(c["key"], tok, c["verify_ctx"])
        assert rc == 0 and out == f"OK {c['expect_scope']}", out

    def test_mint_corpus(self):
        """Minting matches the spec across a large randomized corpus."""
        fails = []
        with (HERE / "vectors_mint.jsonl").open() as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                got = mint(c)
                if got != c["expect"]:
                    fails.append((c, got))
                    if len(fails) > 10:
                        break
        assert not fails, f"{len(fails)} mint mismatches; first: {fails[0]}"

    def test_attenuate_corpus(self):
        """Attenuation (no key) matches the spec across a large randomized corpus."""
        fails = []
        with (HERE / "vectors_att.jsonl").open() as f:
            for line in f:
                if not line.strip():
                    continue
                c = json.loads(line)
                got = attenuate(c["base"], c["caveats"])
                if got != c["expect"]:
                    fails.append((c, got))
                    if len(fails) > 10:
                        break
        assert not fails, f"{len(fails)} attenuate mismatches; first: {fails[0]}"
