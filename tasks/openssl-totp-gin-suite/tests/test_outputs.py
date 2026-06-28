"""Verifier for openssl-totp-gin-suite."""

import hashlib
import hmac
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

SESSION_PATH = Path("/app/output/run_ledger.json")
SEEDS_PATH = Path("/app/environment/data/verifier_seeds.json")
INTEGRITY_DOC = Path("/app/environment/docs/harness_integrity.md")
STEP_DRIVER = Path("/app/environment/scripts/step_driver.py")
GRAD_DRIVER = Path("/app/environment/scripts/grad_driver.sh")
CLI_BIN = Path("/app/bin/m3_cli")
BASE_URL = "http://127.0.0.1:9477"
STORE_ROOT = Path("/app/output/store")
PROBE_STORE_ROOT = Path("/app/output/store_probe")
HOST_PIDFILE = Path("/tmp/m3_host.pid")
HOST_LOG = Path("/tmp/m3_host.log")
STEP_SECONDS = 30
ROW_KEYS = {"scenario", "status", "artifact_digest", "kid"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
KID16 = re.compile(r"^[0-9a-f]{16}$")


def _parse_integrity_pins() -> dict[Path, str]:
    text = INTEGRITY_DOC.read_text(encoding="utf-8")
    pins: dict[Path, str] = {}
    for line in text.splitlines():
        match = re.search(r"`(/app/environment/scripts/[^`]+)` \| `([0-9a-f]{64})`", line)
        if match:
            pins[Path(match.group(1))] = match.group(2)
    assert STEP_DRIVER in pins
    assert GRAD_DRIVER in pins
    return pins


INTEGRITY_PINS = _parse_integrity_pins()


def _start_host() -> None:
    if HOST_PIDFILE.exists():
        try:
            os.kill(int(HOST_PIDFILE.read_text(encoding="utf-8").strip()), 0)
            return
        except OSError:
            pass
    env = os.environ.copy()
    env["M3_LISTEN"] = "127.0.0.1:9477"
    log_fp = open(HOST_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        ["/app/bin/m3_host"],
        stdout=log_fp,
        stderr=subprocess.STDOUT,
        env=env,
    )
    HOST_PIDFILE.write_text(f"{proc.pid}\n", encoding="utf-8")
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{BASE_URL}/healthz", timeout=1) as resp:
                if resp.status == 200:
                    return
        except urllib.error.URLError:
            time.sleep(0.25)
    raise RuntimeError("host failed to start")


def _stop_host() -> None:
    if not HOST_PIDFILE.exists():
        return
    try:
        pid = int(HOST_PIDFILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 15)
    except (ProcessLookupError, OSError, ValueError):
        pass
    HOST_PIDFILE.unlink(missing_ok=True)


def _run_cmd(argv: list[str], env: dict | None = None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        env=merged,
        check=False,
    )


def _post_json(path: str, body: dict, clock: int) -> tuple[int, dict]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Clock-Epoch": str(clock),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            return resp.status, payload
    except urllib.error.HTTPError as exc:
        payload = json.loads(exc.read().decode("utf-8"))
        return exc.code, payload


def _digest_hex(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _material_epoch(host_epoch: int, passcode_epoch: int, step_seconds: int = STEP_SECONDS) -> int:
    """Independent dual-epoch blend matching the public host contract."""
    if host_epoch == passcode_epoch:
        return passcode_epoch
    delta = host_epoch - passcode_epoch
    steps = delta // step_seconds
    if -1 <= steps <= 1:
        return host_epoch
    return passcode_epoch


def _pack_counter_be(counter: int) -> bytes:
    return struct.pack(">Q", counter)


def _derive_passcode(secret: bytes, material_epoch: int, step_seconds: int = STEP_SECONDS) -> str:
    """RFC4226-style HOTP passcode computed independently of the C CLI."""
    counter = material_epoch // step_seconds
    msg = _pack_counter_be(counter)
    digest = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    bin_code = (
        ((digest[offset] & 0x7F) << 24)
        | (digest[offset + 1] << 16)
        | (digest[offset + 2] << 8)
        | digest[offset + 3]
    )
    return f"{bin_code % 1_000_000:06d}"


def _load_secret_hex(store_root: Path, account_id: str) -> bytes:
    record = json.loads((store_root / f"{account_id}.store").read_text(encoding="utf-8"))
    return bytes.fromhex(record["secret_raw"])


def _replay_scenario(spec: dict, store_root: Path = STORE_ROOT) -> dict:
    """Re-run one seeded scenario through the C CLI without the graded driver script."""
    name = spec["name"]
    handle = spec["handle"]
    clock_base = int(spec.get("clock_epoch", 1700000040))
    offset_steps = int(spec.get("clock_offset_steps", 0))
    clock_host = clock_base + offset_steps * STEP_SECONDS
    clock_passcode = clock_base

    env = {
        "K9_CLOCK_EPOCH": str(clock_host),
        "K9_PASSCODE_EPOCH": str(clock_passcode),
    }
    store_root.mkdir(parents=True, exist_ok=True)

    row = {
        "scenario": name,
        "status": spec["expect_status"],
        "artifact_digest": "",
        "kid": "",
    }

    if spec.get("duplicate_enroll"):
        first = _run_cmd([str(CLI_BIN), "enroll", "--handle", handle, "--store-dir", str(store_root)], env)
        if first.returncode != 0:
            row["status"] = "store_reject"
            return row
        second = _run_cmd([str(CLI_BIN), "enroll", "--handle", handle, "--store-dir", str(store_root)], env)
        if second.returncode == 10:
            row["status"] = "enroll_reject"
        else:
            row["status"] = "store_reject"
        return row

    enroll = _run_cmd(
        [
            str(CLI_BIN),
            "enroll",
            "--handle",
            handle,
            "--store-dir",
            str(store_root),
            "--base-url",
            BASE_URL,
        ],
        env,
    )
    if enroll.returncode != 0:
        row["status"] = "store_reject"
        return row
    account_id = enroll.stdout.strip()

    if spec.get("check_store_mode"):
        store_path = store_root / f"{account_id}.store"
        mode = stat.S_IMODE(store_path.stat().st_mode)
        if mode != 0o600:
            row["status"] = "store_reject"
            return row

    if spec.get("bad_passcode"):
        code, _payload = _post_json(
            "/v1/sessions/mfa",
            {"account_id": account_id, "passcode": "000000"},
            clock_host,
        )
        if code == 401:
            row["status"] = "totp_reject"
        else:
            row["status"] = "store_reject"
        return row

    mfa = _run_cmd(
        [
            str(CLI_BIN),
            "mfa",
            "--account-id",
            account_id,
            "--store-dir",
            str(store_root),
            "--base-url",
            BASE_URL,
            "--clock-epoch",
            str(clock_host),
        ],
        env,
    )
    if mfa.returncode == 11:
        row["status"] = "totp_reject"
        return row
    if mfa.returncode != 0:
        row["status"] = "store_reject"
        return row
    token = mfa.stdout.strip()

    if spec.get("rotate_signing") or spec.get("rotate_stale_seal"):
        code, payload = _post_json("/v1/accounts/rotate", {"account_id": account_id}, clock_host)
        if code != 200:
            row["status"] = "store_reject"
            return row
        store_path = store_root / f"{account_id}.store"
        record = json.loads(store_path.read_text(encoding="utf-8"))
        record["signing_material"] = payload["signing_material"]
        store_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        os.chmod(store_path, 0o600)
        old_verify = _run_cmd(
            [
                str(CLI_BIN),
                "verify",
                "--account-id",
                account_id,
                "--token",
                token,
                "--store-dir",
                str(store_root),
                "--clock-epoch",
                str(clock_host),
            ],
            env,
        )
        if spec.get("rotate_stale_seal"):
            if old_verify.returncode == 12:
                row["status"] = "seal_reject"
            else:
                row["status"] = "store_reject"
            return row
        if old_verify.returncode != 12:
            row["status"] = "seal_reject" if spec["expect_status"] != "ok" else "store_reject"
            return row
        mfa2 = _run_cmd(
            [
                str(CLI_BIN),
                "mfa",
                "--account-id",
                account_id,
                "--store-dir",
                str(store_root),
                "--base-url",
                BASE_URL,
                "--clock-epoch",
                str(clock_host),
            ],
            env,
        )
        if mfa2.returncode != 0:
            row["status"] = "store_reject"
            return row
        token = mfa2.stdout.strip()

    if spec.get("tamper_token"):
        token = token[:-1] + ("a" if token[-1] != "a" else "b")

    verify = _run_cmd(
        [
            str(CLI_BIN),
            "verify",
            "--account-id",
            account_id,
            "--token",
            token,
            "--store-dir",
            str(store_root),
            "--clock-epoch",
            str(clock_host),
        ],
        env,
    )
    if verify.returncode == 12:
        row["status"] = "seal_reject"
        return row
    if verify.returncode != 0:
        row["status"] = "store_reject"
        return row

    row["status"] = "ok"
    row["artifact_digest"] = _digest_hex(token)
    row["kid"] = account_id[:16]
    return row


def _independent_suite_payload() -> dict:
    shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
    _start_host()
    try:
        manifest = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
        runs = [_replay_scenario(spec, PROBE_STORE_ROOT) for spec in manifest["scenarios"]]
        return {"runs": runs}
    finally:
        _stop_host()


def _run_suite():
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    if SESSION_PATH.exists():
        SESSION_PATH.unlink()
    subprocess.run(
        [
            "/app/environment/scripts/grad_driver.sh",
            "--session-out",
            "/app/output/run_ledger.json",
        ],
        check=True,
        text=True,
    )


def _row(payload, name):
    for entry in payload["runs"]:
        if entry["scenario"] == name:
            return entry
    raise KeyError(name)


def _expected_specs():
    manifest = json.loads(SEEDS_PATH.read_text(encoding="utf-8"))
    return {spec["name"]: spec for spec in manifest["scenarios"]}


@pytest.fixture(scope="module")
def session_payload():
    _run_suite()
    return json.loads(SESSION_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def independent_payload():
    return _independent_suite_payload()


class TestOutputs:
    def test_ledger_schema(self, session_payload):
        """Every run row exposes the public ledger fields."""
        assert "runs" in session_payload
        for entry in session_payload["runs"]:
            assert ROW_KEYS.issubset(entry.keys())

    def test_suite_covers_all_seed_names(self, session_payload):
        """The graded ledger includes every seeded scenario name exactly once."""
        expected = set(_expected_specs())
        observed = [entry["scenario"] for entry in session_payload["runs"]]
        assert len(observed) == len(expected)
        assert set(observed) == expected
        assert len(observed) == len(set(observed))

    def test_alpha_auth_path(self, session_payload):
        """Happy path enroll, MFA, and local seal verification."""
        row = _row(session_payload, "alpha_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_offset_window_auth(self, session_payload):
        """Adjacent step within the configured window succeeds."""
        row = _row(session_payload, "offset_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_stale_window_rejected(self, session_payload):
        """Out-of-window passcodes are rejected."""
        row = _row(session_payload, "stale_step")
        assert row["status"] == "totp_reject"
        assert row["artifact_digest"] == ""
        assert row["kid"] == ""

    def test_duplex_enroll_rejected(self, session_payload):
        """Duplicate enrollment returns enroll_reject."""
        row = _row(session_payload, "duplex_enroll")
        assert row["status"] == "enroll_reject"
        assert row["artifact_digest"] == ""

    def test_corrupt_token_reject(self, session_payload):
        """Tampered session seals fail local verification."""
        row = _row(session_payload, "corrupt_seal")
        assert row["status"] == "seal_reject"
        assert row["artifact_digest"] == ""

    def test_store_permission_mode(self, session_payload):
        """Local store persistence uses mode 0600 on success paths."""
        row = _row(session_payload, "store_perm")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_signing_rotate_auth(self, session_payload):
        """Rotated signing material invalidates prior seals but accepts fresh MFA."""
        row = _row(session_payload, "signing_rotate_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_beta_auth_path(self, session_payload):
        """Alternate clock base completes enroll, MFA, and seal verification."""
        row = _row(session_payload, "beta_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_minus_offset_window(self, session_payload):
        """Negative host clock offset within the passcode window succeeds."""
        row = _row(session_payload, "minus_offset_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_wide_miss_window(self, session_payload):
        """Host clock offset beyond the configured window is rejected."""
        row = _row(session_payload, "wide_miss_lane")
        assert row["status"] == "totp_reject"
        assert row["artifact_digest"] == ""
        assert row["kid"] == ""

    def test_gamma_auth_path(self, session_payload):
        """Second store-permission success path at a distinct clock base."""
        row = _row(session_payload, "gamma_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_duplex_beta(self, session_payload):
        """Duplicate enrollment on another handle returns enroll_reject."""
        row = _row(session_payload, "duplex_beta")
        assert row["status"] == "enroll_reject"
        assert row["artifact_digest"] == ""

    def test_corrupt_beta(self, session_payload):
        """Tampered seals on a second handle fail local verification."""
        row = _row(session_payload, "corrupt_beta")
        assert row["status"] == "seal_reject"
        assert row["artifact_digest"] == ""

    def test_stale_wide(self, session_payload):
        """Hard-coded out-of-window passcodes are rejected on another handle."""
        row = _row(session_payload, "stale_wide")
        assert row["status"] == "totp_reject"
        assert row["artifact_digest"] == ""

    def test_rotate_stale_token(self, session_payload):
        """Pre-rotation session seals fail after signing material refresh."""
        row = _row(session_payload, "rotate_stale_seal")
        assert row["status"] == "seal_reject"
        assert row["artifact_digest"] == ""

    def test_signing_rotate_beta(self, session_payload):
        """Signing refresh on an alternate clock base accepts a new seal."""
        row = _row(session_payload, "signing_rotate_beta")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_zeta_auth_path(self, session_payload):
        """Combined clock base advance and positive offset within window."""
        row = _row(session_payload, "zeta_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_iota_auth_path(self, session_payload):
        """Higher clock base with positive host offset within window."""
        row = _row(session_payload, "iota_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_lambda_auth_path(self, session_payload):
        """Distinct clock base with negative offset and store mode check."""
        row = _row(session_payload, "lambda_lane")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_omicron_rotate(self, session_payload):
        """Signing refresh at an advanced clock base accepts a new seal."""
        row = _row(session_payload, "omicron_rotate")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_nu_dual_window(self, session_payload):
        """Dual-epoch offset with store permission check at an advanced base."""
        row = _row(session_payload, "nu_dual_window")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_upsilon_wide_ok(self, session_payload):
        """Negative host offset within the passcode window at a distinct base."""
        row = _row(session_payload, "upsilon_wide_ok")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])

    def test_rho_deep_rotate(self, session_payload):
        """Signing refresh with store mode check at a high clock base."""
        row = _row(session_payload, "rho_deep_rotate")
        assert row["status"] == "ok"
        assert HEX64.fullmatch(row["artifact_digest"])
        assert KID16.fullmatch(row["kid"])

    def test_failure_rows_blank_digest(self, session_payload):
        """Non-ok rows leave artifact_digest and kid empty."""
        specs = _expected_specs()
        for entry in session_payload["runs"]:
            if specs[entry["scenario"]]["expect_status"] != "ok":
                assert entry["artifact_digest"] == ""
                assert entry["kid"] == ""

    def test_ok_rows_lowercase_hex(self, session_payload):
        """Successful rows use lowercase hex digests."""
        for entry in session_payload["runs"]:
            if entry["status"] == "ok":
                assert entry["artifact_digest"] == entry["artifact_digest"].lower()

    def test_graded_driver_scripts_unmodified(self):
        """The graded driver scripts still orchestrate live CLI runs instead of fabricating rows."""
        for path, expected in INTEGRITY_PINS.items():
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            assert observed == expected

    def test_terminal_statuses_match_independent_replay(
        self, session_payload, independent_payload
    ):
        """Every terminal status matches an independent C CLI replay of the seed matrix."""
        observed = {row["scenario"]: row["status"] for row in session_payload["runs"]}
        expected = {row["scenario"]: row["status"] for row in independent_payload["runs"]}
        assert observed == expected

    def test_ok_row_kids_reference_persisted_store_accounts(self, session_payload):
        """Successful kid values come from real enrollment store files, not dummy identifiers."""
        store_ids = {path.stem for path in STORE_ROOT.glob("*.store")}
        assert store_ids
        for entry in session_payload["runs"]:
            if entry["status"] != "ok":
                continue
            matches = [account_id for account_id in store_ids if account_id[:16] == entry["kid"]]
            assert len(matches) == 1
            assert matches[0][:16] == entry["kid"]

    def test_graded_run_persisted_enrollment_stores(self, session_payload):
        """The graded suite leaves enrollment artifacts from live CLI runs on disk."""
        store_count = len(list(STORE_ROOT.glob("*.store")))
        ok_count = sum(1 for entry in session_payload["runs"] if entry["status"] == "ok")
        assert store_count >= ok_count

    def test_ok_digests_are_pairwise_unique(self, session_payload):
        """Each successful scenario publishes a distinct session fingerprint."""
        ok_digests = [
            entry["artifact_digest"]
            for entry in session_payload["runs"]
            if entry["status"] == "ok"
        ]
        assert len(ok_digests) >= 8
        assert len(ok_digests) == len(set(ok_digests))

    def test_ok_digests_are_not_placeholder_values(self, session_payload):
        """Successful digests come from real session tokens rather than dummy hex."""
        ok_digests = [
            entry["artifact_digest"]
            for entry in session_payload["runs"]
            if entry["status"] == "ok"
        ]
        assert ok_digests
        assert len(set(ok_digests)) >= 8
        assert all(digest != ("0" * 64) for digest in ok_digests)
        assert all(digest != ("a" * 64) for digest in ok_digests)

    def test_independent_passcode_matches_host_mfa(self):
        """Passcode materialization matches an independent Python HOTP replay."""
        _start_host()
        shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
        PROBE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            clock_base = 1700000040
            env = {
                "K9_CLOCK_EPOCH": str(clock_base),
                "K9_PASSCODE_EPOCH": str(clock_base),
            }
            enroll = _run_cmd(
                [
                    str(CLI_BIN),
                    "enroll",
                    "--handle",
                    "alpha_lane",
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                ],
                env,
            )
            assert enroll.returncode == 0
            assert enroll.stdout.strip()
            account_id = enroll.stdout.strip()
            secret = _load_secret_hex(PROBE_STORE_ROOT, account_id)
            material = _material_epoch(clock_base, clock_base)
            expected_code = _derive_passcode(secret, material)
            code, payload = _post_json(
                "/v1/sessions/mfa",
                {"account_id": account_id, "passcode": expected_code},
                clock_base,
            )
            assert code == 200
            token = payload["session_token"]
            assert token
            assert _digest_hex(token) != ("0" * 64)
        finally:
            _stop_host()

    def test_passcode_epoch_mutation_changes_ok_fingerprint(self, session_payload):
        """Changing passcode epoch binding must change successful session fingerprints."""
        alpha = _row(session_payload, "alpha_lane")
        offset = _row(session_payload, "offset_lane")
        assert alpha["status"] == "ok" and offset["status"] == "ok"
        assert alpha["artifact_digest"] != offset["artifact_digest"]

    def test_verify_subcommand_rejects_tampered_token(self):
        """The documented verify subcommand rejects tampered session seals locally."""
        _start_host()
        shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
        PROBE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            clock = 1700000040
            env = {"K9_CLOCK_EPOCH": str(clock), "K9_PASSCODE_EPOCH": str(clock)}
            enroll = _run_cmd(
                [
                    str(CLI_BIN),
                    "enroll",
                    "--handle",
                    "corrupt_seal",
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                ],
                env,
            )
            assert enroll.returncode == 0
            account_id = enroll.stdout.strip()
            mfa = _run_cmd(
                [
                    str(CLI_BIN),
                    "mfa",
                    "--account-id",
                    account_id,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                    "--clock-epoch",
                    str(clock),
                ],
                env,
            )
            assert mfa.returncode == 0
            token = mfa.stdout.strip()
            assert token
            bad_token = token[:-1] + ("a" if token[-1] != "a" else "b")
            verify = _run_cmd(
                [
                    str(CLI_BIN),
                    "verify",
                    "--account-id",
                    account_id,
                    "--token",
                    bad_token,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--clock-epoch",
                    str(clock),
                ],
                env,
            )
            assert verify.returncode == 12
            assert "verified" not in verify.stdout
        finally:
            _stop_host()

    def test_wide_miss_window_is_totp_reject_not_ok(self, session_payload):
        """Out-of-window host offsets must not land in the ok bucket."""
        row = _row(session_payload, "wide_miss_lane")
        assert row["status"] == "totp_reject"
        assert row["status"] != "ok"

    def test_ok_rows_use_persisted_store_material(self, session_payload):
        """Successful rows must reference enrollment stores that still hold account material."""
        specs = _expected_specs()
        for entry in session_payload["runs"]:
            if entry["status"] != "ok":
                continue
            spec = specs[entry["scenario"]]
            matches = [
                path
                for path in STORE_ROOT.glob("*.store")
                if path.stem[:16] == entry["kid"]
            ]
            assert len(matches) == 1
            record = json.loads(matches[0].read_text(encoding="utf-8"))
            assert record["account_id"] == matches[0].stem
            assert record["secret_raw"]
            assert record["signing_material"]
            if spec.get("check_store_mode"):
                mode = stat.S_IMODE(matches[0].stat().st_mode)
                assert mode == 0o600

    def test_probe_subcommand_emits_six_digit_code(self):
        """The documented probe subcommand prints a six-digit passcode for a persisted account."""
        _start_host()
        shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
        PROBE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            clock = 1700000040
            env = {"K9_CLOCK_EPOCH": str(clock), "K9_PASSCODE_EPOCH": str(clock)}
            enroll = _run_cmd(
                [
                    str(CLI_BIN),
                    "enroll",
                    "--handle",
                    "alpha_lane",
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                ],
                env,
            )
            assert enroll.returncode == 0
            account_id = enroll.stdout.strip()
            probe = _run_cmd(
                [
                    str(CLI_BIN),
                    "probe",
                    "--account-id",
                    account_id,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--clock-epoch",
                    str(clock),
                ],
                env,
            )
            assert probe.returncode == 0
            code = probe.stdout.strip()
            assert len(code) == 6
            assert code.isdigit()
        finally:
            _stop_host()

    def test_probe_passcode_tracks_passcode_epoch_binding(self):
        """Changing K9_PASSCODE_EPOCH must change probe output while host epoch stays fixed."""
        _start_host()
        shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
        PROBE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            clock_base = 1700000040
            host_epoch = clock_base + STEP_SECONDS
            base_env = {
                "K9_CLOCK_EPOCH": str(host_epoch),
                "K9_PASSCODE_EPOCH": str(clock_base),
            }
            enroll = _run_cmd(
                [
                    str(CLI_BIN),
                    "enroll",
                    "--handle",
                    "offset_lane",
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                ],
                base_env,
            )
            assert enroll.returncode == 0
            account_id = enroll.stdout.strip()
            probe_a = _run_cmd(
                [
                    str(CLI_BIN),
                    "probe",
                    "--account-id",
                    account_id,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--clock-epoch",
                    str(host_epoch),
                ],
                base_env,
            )
            shifted_env = {
                "K9_CLOCK_EPOCH": str(host_epoch),
                "K9_PASSCODE_EPOCH": str(clock_base - STEP_SECONDS),
            }
            probe_b = _run_cmd(
                [
                    str(CLI_BIN),
                    "probe",
                    "--account-id",
                    account_id,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--clock-epoch",
                    str(host_epoch),
                ],
                shifted_env,
            )
            assert probe_a.returncode == 0
            assert probe_b.returncode == 0
            assert probe_a.stdout.strip() != probe_b.stdout.strip()
        finally:
            _stop_host()

    def test_probe_matches_independent_python_derivation(self):
        """Probe output must match an independent Python passcode derivation."""
        _start_host()
        shutil.rmtree(PROBE_STORE_ROOT, ignore_errors=True)
        PROBE_STORE_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            clock_base = 1700000040
            host_epoch = clock_base + STEP_SECONDS
            env = {
                "K9_CLOCK_EPOCH": str(host_epoch),
                "K9_PASSCODE_EPOCH": str(clock_base),
            }
            enroll = _run_cmd(
                [
                    str(CLI_BIN),
                    "enroll",
                    "--handle",
                    "offset_lane",
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--base-url",
                    BASE_URL,
                ],
                env,
            )
            assert enroll.returncode == 0
            account_id = enroll.stdout.strip()
            secret = _load_secret_hex(PROBE_STORE_ROOT, account_id)
            material = _material_epoch(host_epoch, clock_base)
            expected = _derive_passcode(secret, material)
            probe = _run_cmd(
                [
                    str(CLI_BIN),
                    "probe",
                    "--account-id",
                    account_id,
                    "--store-dir",
                    str(PROBE_STORE_ROOT),
                    "--clock-epoch",
                    str(host_epoch),
                ],
                env,
            )
            assert probe.returncode == 0
            assert probe.stdout.strip() == expected
        finally:
            _stop_host()
