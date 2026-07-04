import os
import subprocess
import json
import random
import tempfile
from pathlib import Path

import pytest

ENV = Path(os.environ.get("TASK_ENV", "/app/environment"))
BIN_DIR = ENV / "bin"
BIN = Path(os.environ.get("TASK_BIN", str(BIN_DIR / "mwtool")))
VALID_DIR = ENV / "testdata" / "valid"
EXPLOIT_DIR = ENV / "testdata" / "exploits"


@pytest.fixture(scope="session", autouse=True)
def build_cli():
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["go", "build", "-o", str(BIN), "./cmd/mwtool"],
        cwd=ENV,
        check=True,
    )
    subprocess.run(
        ["go", "build", "-o", str(BIN.with_name("mw-runner")), "./cmd/mw-runner"],
        cwd=ENV,
        check=True,
    )
    return BIN


ASAN_SIGNATURES = (
    "addresssanitizer",
    "heap-buffer-overflow",
    "stack-buffer-overflow",
    "heap-use-after-free",
    "==error==",
    "shadow bytes around",
    "summary: addresssanitizer",
)


def assert_clean_rejection(
    result: subprocess.CompletedProcess,
    fixture_name: str,
    domain_keywords: list[str] | None = None,
) -> None:
    assert result.returncode != 0, f"{fixture_name} should be rejected"
    err_lower = (result.stderr or "").lower()
    assert all(sig not in err_lower for sig in ASAN_SIGNATURES), (
        f"{fixture_name} shows sanitizer output in stderr\n{result.stderr}"
    )
    assert len(result.stderr or "") > 0, f"{fixture_name} produced no error message"
    if domain_keywords:
        assert any(kw in err_lower for kw in domain_keywords), (
            f"{fixture_name} stderr does not identify the failing check: {result.stderr}"
        )


def run_config(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(BIN), str(path)], capture_output=True, text=True, timeout=5
    )


def load_valid(name: str) -> dict:
    with open(VALID_DIR / name) as f:
        return json.load(f)


def run_config_obj(cfg: dict) -> subprocess.CompletedProcess:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
        json.dump(cfg, tf)
        tf_path = Path(tf.name)
    try:
        return run_config(tf_path)
    finally:
        tf_path.unlink()


def test_valid_configs_all_pass():
    for cfg in sorted(VALID_DIR.glob("valid_*.json")):
        result = run_config(cfg)
        assert result.returncode == 0, (
            f"{cfg.name} should pass\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


def test_exploit_binary_rejected():
    result = run_config(EXPLOIT_DIR / "exploit_binary.json")
    assert_clean_rejection(result, "exploit_binary", ["binary", "allowlist"])


def test_exploit_local_rejected():
    result = run_config(EXPLOIT_DIR / "exploit_local.json")
    assert_clean_rejection(result, "exploit_local", ["local", "script"])


def test_exploit_remote_rejected():
    result = run_config(EXPLOIT_DIR / "exploit_remote.json")
    assert_clean_rejection(result, "exploit_remote", ["remote", "path"])


def test_exploit_api_rejected():
    result = run_config(EXPLOIT_DIR / "exploit_api.json")
    assert_clean_rejection(result, "exploit_api", ["api", "token", "auth"])


def test_exploit_token_rejected():
    result = run_config(EXPLOIT_DIR / "exploit_token.json")
    assert_clean_rejection(result, "exploit_token", ["api", "token", "auth"])


def test_security_notes_exists():
    notes = ENV / "security_notes.md"
    assert notes.exists(), "security_notes.md not written"
    body = notes.read_text()
    assert len(body) > 100, "security_notes.md too short"
    components_found = sum(
        tag in body.lower()
        for tag in [
            "config.go",
            "local_exec.go",
            "remote_exec.go",
            "middleware_service.go",
        ]
    )
    assert components_found >= 3, (
        "security_notes.md must document at least 3 of 4 fixed components "
        "(config.go, local_exec.go, remote_exec.go, middleware_service.go)"
    )


def test_no_shortcut_modifications():
    mwtool = (ENV / "cmd/mwtool/main.go").read_text()
    assert "package main" in mwtool
    assert "func main()" in mwtool
    assert "service.NewService" in mwtool

    mw_runner = (ENV / "cmd/mw-runner/main.go").read_text()
    assert "package main" in mw_runner
    assert "func main()" in mw_runner
    assert "io.Copy" in mw_runner


def test_no_hardcoded_exploit_keywords():
    for go_file in ENV.glob("src/**/*.go"):
        content = go_file.read_text().lower()
        assert "e00" not in content, f"Hardcoded exploit ID found in {go_file.name}"
        assert "nope" not in content, f"Hardcoded bypass token found in {go_file.name}"


def test_random_unauthorized_binaries_rejected():
    bad_binaries = ["ls", "cat", "rm", "sh", "bash", "python3"]
    for binary in bad_binaries:
        with open(VALID_DIR / "valid_001.json") as f:
            cfg = json.load(f)
        cfg["middleware"]["binary"] = binary
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(cfg, tf)
            tf_path = Path(tf.name)
        try:
            result = run_config(tf_path)
            assert_clean_rejection(result, f"unauthorized binary {binary}")
        finally:
            tf_path.unlink()


def test_various_unsafe_scripts_rejected():
    unsafe_scripts = [
        "noop; rm -rf /",
        "trim|echo",
        "upper && echo",
        "lower || echo",
        "noop\n/bin/sh",
        "noop`id`",
        "noop$(id)",
        "noop<file",
        "noop>file",
    ]
    for script in unsafe_scripts:
        with open(VALID_DIR / "valid_001.json") as f:
            cfg = json.load(f)
        cfg["middleware"]["script"] = script
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(cfg, tf)
            tf_path = Path(tf.name)
        try:
            result = run_config(tf_path)
            assert_clean_rejection(result, f"unsafe script {script}")
        finally:
            tf_path.unlink()


def test_various_unsafe_remote_paths_rejected():
    unsafe_paths = [
        "testdata/remote/remote_001.json; rm -rf /",
        "testdata/remote/remote_001.json|echo",
        "testdata/remote/remote_001.json&&echo",
        "testdata/remote/remote_001.json||echo",
        "testdata/remote/remote_001.json\n/bin/sh",
        "testdata/remote/remote_001.json`id`",
        "testdata/remote/remote_001.json$(id)",
        "/etc/passwd",
        "../remote/remote_001.json",
    ]
    for path in unsafe_paths:
        with open(VALID_DIR / "valid_004.json") as f:
            cfg = json.load(f)
        cfg["middleware"]["remote_path"] = path
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(cfg, tf)
            tf_path = Path(tf.name)
        try:
            result = run_config(tf_path)
            assert_clean_rejection(result, f"unsafe remote path {path}")
        finally:
            tf_path.unlink()


def test_remote_path_traversal_rejected():
    # Each target shares the "testdata/remote/" prefix but escapes the directory
    # via "..", pointing at a file that genuinely exists elsewhere in the env. A
    # prefix-only check accepts these (it would read the file and exit 0); a
    # correct fix must canonicalize the path and confine reads to the remote dir.
    traversal_paths = [
        "testdata/remote/../valid/valid_001.json",
        "testdata/remote/../../go.mod",
        "testdata/remote/../../src/middleware/config.go",
        "testdata/remote/subdir/../../valid/valid_001.json",
        "testdata/remote/../remote/../valid/valid_004.json",
    ]
    # Sanity-check that these targets actually resolve to real files, so the test
    # truly distinguishes a containment check from a prefix check.
    for path in traversal_paths:
        assert (ENV / path).resolve().exists(), f"traversal fixture {path} must exist"
    for path in traversal_paths:
        with open(VALID_DIR / "valid_004.json") as f:
            cfg = json.load(f)
        cfg["middleware"]["remote_path"] = path
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(cfg, tf)
            tf_path = Path(tf.name)
        try:
            result = run_config(tf_path)
            assert_clean_rejection(
                result, f"remote path traversal {path}", ["remote", "path"]
            )
        finally:
            tf_path.unlink()


def test_unauthorized_tokens_rejected():
    bad_tokens = ["wrong-token", "", "admin", "null"]
    for token in bad_tokens:
        with open(VALID_DIR / "valid_001.json") as f:
            cfg = json.load(f)
        cfg["auth_token"] = token
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tf:
            json.dump(cfg, tf)
            tf_path = Path(tf.name)
        try:
            result = run_config(tf_path)
            assert_clean_rejection(result, f"unauthorized token {token}")
        finally:
            tf_path.unlink()


def test_hidden_binary_variants_reject_cleanly():
    # Binaries outside the allowlist that would nonetheless run to completion
    # under a shell (they exist and exit 0). A general allowlist rejects every
    # one; an under-inclusive denylist that only blocks known-bad shells lets
    # them through and executes attacker-chosen programs.
    variants = [
        "echo",
        "/bin/echo",
        "printf",
        "true",
        "/usr/bin/true",
        ":",
    ]
    for binary in variants:
        cfg = load_valid("valid_001.json")
        cfg["middleware"]["binary"] = binary
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"hidden binary {binary}", ["binary", "allowlist"]
        )


def test_hidden_script_variants_reject_cleanly():
    # Each variant appends a benign-but-successful injection to a valid script,
    # exercising a different shell metacharacter. Under a shell the injection
    # runs and the process exits 0, so only a general fix (metacharacter
    # rejection and/or dropping the shell) refuses them.
    injections = [
        "noop; echo pwned",
        "noop | echo pwned",
        "noop && echo pwned",
        "noop || echo pwned",
        "noop `echo pwned`",
        "noop $(echo pwned)",
        "noop > /dev/null",
        "noop < /dev/null",
        "noop\necho pwned",
        "noop$HOME",
    ]
    for script in injections:
        cfg = load_valid("valid_001.json")
        cfg["middleware"]["script"] = script
        result = run_config_obj(cfg)
        assert_clean_rejection(result, f"hidden script {script!r}", ["local", "script"])


def test_hidden_remote_traversal_variants_reject_cleanly():
    # Extra traversal encodings that resolve to a real file outside
    # testdata/remote/. Most keep the literal "testdata/remote/" prefix, so a
    # prefix check accepts them and reads the file (exit 0); only canonicalizing
    # and confining to the directory rejects them.
    traversal_paths = [
        "testdata//remote/../valid/valid_001.json",
        "testdata/remote/./../valid/valid_001.json",
        "testdata/remote/../valid/./valid_001.json",
        "testdata/remote/x/../../valid/valid_001.json",
        "testdata/remote/../../go.mod",
        "testdata/remote/../../src/middleware/config.go",
        "testdata/remote/sub/deep/../../../valid/valid_004.json",
        "testdata/remote/../remote/../valid/valid_004.json",
    ]
    for path in traversal_paths:
        assert (ENV / path).resolve().exists(), f"traversal fixture {path} must exist"
    for path in traversal_paths:
        cfg = load_valid("valid_004.json")
        cfg["middleware"]["remote_path"] = path
        result = run_config_obj(cfg)
        assert_clean_rejection(result, f"hidden traversal {path}", ["remote", "path"])


def test_fuzz_unauthorized_inputs_rejected():
    # Seeded fuzz loop mixing three unauthorized-input classes. A hardcoded or
    # fixture-shaped fix cannot enumerate these; each must be refused through the
    # general boundary check that owns it.
    rnd = random.Random(20240702)
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    disallowed_binaries = ["echo", "/bin/echo", "printf", "true", "/usr/bin/true", ":"]
    for _ in range(60):
        arm = rnd.choice(["binary", "token", "path"])
        if arm == "binary":
            cfg = load_valid("valid_001.json")
            cfg["middleware"]["binary"] = rnd.choice(disallowed_binaries)
            keywords = ["binary", "allowlist"]
        elif arm == "token":
            cfg = load_valid("valid_001.json")
            token = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(3, 14)))
            cfg["auth_token"] = token
            keywords = ["api", "token", "auth"]
        else:
            cfg = load_valid("valid_004.json")
            segment = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(3, 10)))
            cfg["middleware"]["remote_path"] = f"testdata/remote/../{segment}"
            keywords = ["remote", "path"]
        result = run_config_obj(cfg)
        assert_clean_rejection(result, f"fuzz {arm}", keywords)


def test_hidden_token_variants_reject_cleanly():
    # Near-miss tokens that differ from the admin token only by case or
    # surrounding whitespace. A normalization-unsafe comparison (case-folding
    # and/or trimming before matching) accepts them and grants access; only an
    # exact, byte-for-byte comparison refuses every one. The genuine token is
    # never included here.
    base = "admin-token"
    variants = [
        base.upper(),
        base.capitalize(),
        base.swapcase(),
        "Admin-Token",
        "aDmIn-ToKeN",
        " " + base,
        base + " ",
        "  " + base + "  ",
        "\t" + base,
        base + "\n",
    ]
    for token in variants:
        cfg = load_valid("valid_001.json")
        cfg["auth_token"] = token
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"hidden token {token!r}", ["api", "token", "auth"]
        )


def test_fuzz_token_normalization_rejected():
    # Seeded fuzz over case-permuted and whitespace-padded renderings of the
    # admin token. Each rendering is not the exact token, so an exact comparison
    # rejects it; a case-insensitive or trimming comparison lets it through. The
    # identity rendering (all lowercase, no padding) is skipped.
    rnd = random.Random(20240811)
    base = "admin-token"
    for _ in range(40):
        token = "".join(c.upper() if rnd.random() < 0.5 else c.lower() for c in base)
        if rnd.random() < 0.5:
            token = " " * rnd.randint(1, 3) + token
        if rnd.random() < 0.5:
            token = token + " " * rnd.randint(1, 3)
        if token == base:
            continue
        cfg = load_valid("valid_001.json")
        cfg["auth_token"] = token
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"fuzz token {token!r}", ["api", "token", "auth"]
        )


def test_binary_allowlist_is_exact_match():
    # Near-miss renderings of the approved runner. Membership is decided by an
    # exact comparison, so a trailing space, case change, a relative "./" prefix,
    # or an appended character must all be refused. A fix that trims, lowercases,
    # or substring-matches the field before deciding would wrongly admit some.
    variants = [
        "mw-runner ",
        " mw-runner",
        "mw-runner\t",
        "MW-RUNNER",
        "Mw-Runner",
        "./mw-runner",
        "mw-runnerx",
        "runner",
    ]
    for binary in variants:
        cfg = load_valid("valid_001.json")
        cfg["middleware"]["binary"] = binary
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"binary near-miss {binary!r}", ["binary", "allowlist"]
        )


def test_binary_allowlist_enforced_in_remote_mode():
    # The allowlist must gate every mode, not only local. A remote-mode config
    # that names a real system binary must be refused by the same check, before
    # any file is read or process spawned.
    for binary in ["/bin/cat", "cat", "/usr/bin/env", "sh"]:
        cfg = load_valid("valid_004.json")
        cfg["middleware"]["binary"] = binary
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"remote binary {binary!r}", ["binary", "allowlist"]
        )


def test_api_disabled_blocks_even_with_correct_token():
    # When the middleware API is disabled, no request may configure middleware,
    # even one carrying the correct admin token. A check that inspects only the
    # token value while ignoring the enable flag would wrongly admit this.
    cfg = load_valid("valid_001.json")
    cfg["enable_middleware_api"] = False
    cfg["auth_token"] = "admin-token"
    result = run_config_obj(cfg)
    assert_clean_rejection(
        result, "api disabled with correct token", ["api", "token", "auth"]
    )


def test_token_boundary_variants_rejected():
    # Tokens differing from the admin token by more than case or padding:
    # truncations, extensions, and single-character edits. An exact comparison
    # refuses every one; the genuine token is never present in this list.
    variants = [
        "admin-toke",
        "admin-tokenx",
        "admin-token-extra",
        "admin_token",
        "admin.token",
        "dmin-token",
        "admintoken",
        "ADMINTOKEN",
    ]
    for token in variants:
        cfg = load_valid("valid_001.json")
        cfg["auth_token"] = token
        result = run_config_obj(cfg)
        assert_clean_rejection(
            result, f"token boundary {token!r}", ["api", "token", "auth"]
        )


def test_valid_remote_paths_still_accepted():
    # Confinement must not over-reject legitimate reads inside testdata/remote/.
    for name in ["remote_001.json", "remote_002.json", "remote_003.json"]:
        cfg = load_valid("valid_004.json")
        cfg["middleware"]["remote_path"] = f"testdata/remote/{name}"
        result = run_config_obj(cfg)
        assert result.returncode == 0, (
            f"valid remote path {name} should be accepted\nstderr:\n{result.stderr}"
        )


def test_remote_root_and_escape_paths_rejected():
    # The remote root directory itself, its parent, and paths that normalize
    # outside it must all be refused. Each keeps a plausible-looking prefix or
    # shape yet is not a file confined within testdata/remote/.
    paths = [
        "testdata/remote",
        "testdata/remote/",
        "testdata/remote/..",
        "testdata/../remote/remote_001.json",
        "/etc/hostname",
    ]
    for p in paths:
        cfg = load_valid("valid_004.json")
        cfg["middleware"]["remote_path"] = p
        result = run_config_obj(cfg)
        assert_clean_rejection(result, f"remote path {p!r}", ["remote", "path"])
