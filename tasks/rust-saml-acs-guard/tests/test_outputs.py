import os
import shutil
import subprocess


PKG_DIR = os.environ.get("PKG_DIR", "/app/task_file")
TEST_DIR = os.environ.get("TEST_DIR", "/tests")


def test_saml_acs_security_contract():
    hidden_src = os.path.join(TEST_DIR, "hidden_tests.rs")
    hidden_dst_dir = os.path.join(PKG_DIR, "tests")
    hidden_dst = os.path.join(hidden_dst_dir, "hidden_tests.rs")
    os.makedirs(hidden_dst_dir, exist_ok=True)
    shutil.copyfile(hidden_src, hidden_dst)

    result = subprocess.run(
        ["cargo", "test", "--release", "--locked"],
        cwd=PKG_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout
