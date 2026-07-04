"""Package dependency version resolver verifier.

Pipes fixtures through compiled binary, checks stdout.
"""

import subprocess
import pytest

BIN = ["/app/solver"]
TIMEOUT = 15

FIXTURES = {
    "publish_single": {
        "input": "PUBLISH foo 1.0.0\n",
        "expected": "OK",
    },
    "resolve_simple_caret": {
        "input": "PUBLISH foo 1.0.0\nPUBLISH foo 1.2.0\nADD foo ^1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nRESOLVED\nfoo 1.2.0",
    },
    "resolve_tilde": {
        "input": "PUBLISH bar 1.0.0\nPUBLISH bar 1.0.5\nPUBLISH bar 1.1.0\nADD bar ~1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nbar 1.0.5",
    },
    "resolve_exact": {
        "input": "PUBLISH baz 2.0.0\nPUBLISH baz 2.1.0\nADD baz 2.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nRESOLVED\nbaz 2.0.0",
    },
    "resolve_gte": {
        "input": "PUBLISH lib 1.0.0\nPUBLISH lib 2.0.0\nPUBLISH lib 3.0.0\nADD lib >=2.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nlib 3.0.0",
    },
    "resolve_range": {
        "input": "PUBLISH x 1.0.0\nPUBLISH x 1.5.0\nPUBLISH x 2.0.0\nADD x >=1.0.0 <2.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nx 1.5.0",
    },
    "yank_excludes_version": {
        "input": "PUBLISH foo 1.0.0\nPUBLISH foo 1.1.0\nYANK foo 1.1.0\nADD foo ^1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nYANKED foo 1.1.0\nOK\nRESOLVED\nfoo 1.0.0",
    },
    "dependency_resolution": {
        "input": "PUBLISH app 1.0.0\nPUBLISH lib 2.0.0\nPUBLISH lib 2.1.0\nDEPEND app 1.0.0 lib ^2.0.0\nADD app ^1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nOK\nRESOLVED\napp 1.0.0\nlib 2.1.0",
    },
    "conflict_no_version": {
        "input": "PUBLISH foo 1.0.0\nADD foo ^2.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nCONFLICT foo ^2.0.0",
    },
    "lock_basic": {
        "input": "PUBLISH foo 1.0.0\nPUBLISH foo 1.5.0\nADD foo ^1.0.0\nLOCK foo 1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nLOCKED foo 1.0.0\nRESOLVED\nfoo 1.0.0",
    },
    "lock_error_violates_constraint": {
        "input": "PUBLISH foo 1.0.0\nPUBLISH foo 2.0.0\nADD foo ^2.0.0\nLOCK foo 1.0.0\n",
        "expected": "OK\nOK\nOK\nLOCK_ERROR foo 1.0.0",
    },
    "upgrade_to_highest": {
        "input": "PUBLISH foo 1.0.0\nPUBLISH foo 1.3.0\nPUBLISH foo 1.5.0\nADD foo ^1.0.0\nLOCK foo 1.0.0\nUPGRADE foo\n",
        "expected": "OK\nOK\nOK\nOK\nLOCKED foo 1.0.0\nUPGRADED foo 1.5.0",
    },
    "upgrade_no_change": {
        "input": "PUBLISH foo 1.5.0\nADD foo ^1.0.0\nLOCK foo 1.5.0\nUPGRADE foo\n",
        "expected": "OK\nOK\nLOCKED foo 1.5.0\nNO_UPGRADE",
    },
    "multiple_packages_alphabetical": {
        "input": "PUBLISH zeta 1.0.0\nPUBLISH alpha 2.0.0\nADD zeta ^1.0.0\nADD alpha ^2.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nalpha 2.0.0\nzeta 1.0.0",
    },
    "caret_respects_major": {
        "input": "PUBLISH foo 1.9.9\nPUBLISH foo 2.0.0\nADD foo ^1.0.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nRESOLVED\nfoo 1.9.9",
    },
    "tilde_respects_minor": {
        "input": "PUBLISH bar 1.2.0\nPUBLISH bar 1.2.9\nPUBLISH bar 1.3.0\nADD bar ~1.2.0\nRESOLVE\n",
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nbar 1.2.9",
    },
    "diamond_dependency": {
        "input": (
            "PUBLISH app 1.0.0\n"
            "PUBLISH web 1.0.0\n"
            "PUBLISH util 1.2.0\n"
            "PUBLISH util 1.3.0\n"
            "PUBLISH util 1.4.0\n"
            "DEPEND app 1.0.0 util ^1.2.0\n"
            "DEPEND web 1.0.0 util ~1.3.0\n"
            "ADD app ^1.0.0\n"
            "ADD web ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nOK\nOK\nOK\nOK\nRESOLVED\napp 1.0.0\nutil 1.3.0\nweb 1.0.0",
    },
    "diamond_conflict": {
        "input": (
            "PUBLISH app 1.0.0\n"
            "PUBLISH web 1.0.0\n"
            "PUBLISH util 1.5.0\n"
            "DEPEND app 1.0.0 util ^1.0.0\n"
            "DEPEND web 1.0.0 util ^2.0.0\n"
            "ADD app ^1.0.0\n"
            "ADD web ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nOK\nOK\nCONFLICT util ^1.0.0",
    },
    "backtrack_to_lower_version": {
        "input": (
            "PUBLISH srv 2.0.0\n"
            "PUBLISH srv 1.0.0\n"
            "PUBLISH db 3.0.0\n"
            "PUBLISH db 2.5.0\n"
            "PUBLISH lib 1.0.0\n"
            "DEPEND srv 2.0.0 lib ^2.0.0\n"
            "DEPEND srv 1.0.0 lib ^1.0.0\n"
            "ADD srv ^1.0.0\n"
            "ADD lib ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nOK\nOK\nOK\nOK\nRESOLVED\nlib 1.0.0\nsrv 1.0.0",
    },
    "unlock_basic": {
        "input": (
            "PUBLISH foo 1.0.0\n"
            "PUBLISH foo 1.5.0\n"
            "ADD foo ^1.0.0\n"
            "LOCK foo 1.0.0\n"
            "UNLOCK foo\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nLOCKED foo 1.0.0\nUNLOCKED foo\nRESOLVED\nfoo 1.5.0",
    },
    "unlock_error_not_locked": {
        "input": "PUBLISH foo 1.0.0\nUNLOCK foo\n",
        "expected": "OK\nUNLOCK_ERROR foo",
    },
    "remove_package": {
        "input": (
            "PUBLISH foo 1.0.0\n"
            "PUBLISH bar 2.0.0\n"
            "ADD foo ^1.0.0\n"
            "ADD bar ^2.0.0\n"
            "REMOVE foo\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nREMOVED foo\nRESOLVED\nbar 2.0.0",
    },
    "remove_clears_lock": {
        "input": (
            "PUBLISH foo 1.0.0\n"
            "ADD foo ^1.0.0\n"
            "LOCK foo 1.0.0\n"
            "REMOVE foo\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nLOCKED foo 1.0.0\nREMOVED foo\nRESOLVED",
    },
    "transitive_chain_three_deep": {
        "input": (
            "PUBLISH app 1.0.0\n"
            "PUBLISH mid 1.0.0\n"
            "PUBLISH leaf 1.0.0\n"
            "PUBLISH leaf 1.1.0\n"
            "DEPEND app 1.0.0 mid ^1.0.0\n"
            "DEPEND mid 1.0.0 leaf ~1.0.0\n"
            "ADD app ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nOK\nOK\nRESOLVED\napp 1.0.0\nleaf 1.0.0\nmid 1.0.0",
    },
    "yank_forces_backtrack": {
        "input": (
            "PUBLISH core 1.0.0\n"
            "PUBLISH core 1.1.0\n"
            "PUBLISH core 1.2.0\n"
            "PUBLISH plug 1.0.0\n"
            "DEPEND plug 1.0.0 core ~1.1.0\n"
            "YANK core 1.1.0\n"
            "ADD plug ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nYANKED core 1.1.0\nOK\nCONFLICT core ~1.1.0",
    },
    "prerelease_excluded_by_caret": {
        "input": (
            "PUBLISH sdk 1.0.0-beta.1\n"
            "PUBLISH sdk 1.0.0-rc.1\n"
            "PUBLISH sdk 0.9.0\n"
            "ADD sdk ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nCONFLICT sdk ^1.0.0",
    },
    "prerelease_matched_by_pre_constraint": {
        "input": (
            "PUBLISH sdk 1.0.0-beta.1\n"
            "PUBLISH sdk 1.0.0-rc.1\n"
            "PUBLISH sdk 1.0.0\n"
            "ADD sdk ^1.0.0-beta.1\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nsdk 1.0.0",
    },
    "prerelease_sort_order": {
        "input": (
            "PUBLISH lib 1.0.0-alpha.1\n"
            "PUBLISH lib 1.0.0-beta.1\n"
            "PUBLISH lib 1.0.0\n"
            "PUBLISH lib 0.9.9\n"
            "ADD lib ^1.0.0-alpha.1\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nRESOLVED\nlib 1.0.0",
    },
    "prerelease_tilde_excludes": {
        "input": (
            "PUBLISH pkg 2.1.0-rc.1\n"
            "PUBLISH pkg 2.1.0\n"
            "PUBLISH pkg 2.1.1\n"
            "ADD pkg ~2.1.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\npkg 2.1.1",
    },
    "prerelease_only_available": {
        "input": (
            "PUBLISH tool 3.0.0-beta.1\n"
            "PUBLISH tool 3.0.0-beta.2\n"
            "ADD tool ^3.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nCONFLICT tool ^3.0.0",
    },
    "multi_resolve_state_persists": {
        "input": (
            "PUBLISH foo 1.0.0\n"
            "PUBLISH foo 1.1.0\n"
            "ADD foo ^1.0.0\n"
            "RESOLVE\n"
            "PUBLISH foo 1.2.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nRESOLVED\nfoo 1.1.0\nOK\nRESOLVED\nfoo 1.2.0",
    },
    "yank_after_resolve_changes_result": {
        "input": (
            "PUBLISH net 2.0.0\n"
            "PUBLISH net 2.1.0\n"
            "PUBLISH net 2.2.0\n"
            "ADD net ^2.0.0\n"
            "RESOLVE\n"
            "YANK net 2.2.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nRESOLVED\nnet 2.2.0\nYANKED net 2.2.0\nRESOLVED\nnet 2.1.0",
    },
    "deep_backtrack_with_prerelease": {
        "input": (
            "PUBLISH app 2.0.0\n"
            "PUBLISH app 1.0.0\n"
            "PUBLISH db 1.0.0\n"
            "PUBLISH db 1.0.0-rc.1\n"
            "DEPEND app 2.0.0 db ^1.0.0-rc.1\n"
            "DEPEND app 1.0.0 db ^1.0.0\n"
            "ADD app ^1.0.0\n"
            "ADD db ^1.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nOK\nOK\nOK\nRESOLVED\napp 1.0.0\ndb 1.0.0",
    },
    "remove_keeps_transitive": {
        "input": (
            "PUBLISH app 1.0.0\n"
            "PUBLISH lib 1.0.0\n"
            "DEPEND app 1.0.0 lib ^1.0.0\n"
            "ADD app ^1.0.0\n"
            "ADD lib ^1.0.0\n"
            "REMOVE lib\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nOK\nOK\nREMOVED lib\nRESOLVED\napp 1.0.0\nlib 1.0.0",
    },
    "conflict_reports_first_constraint": {
        "input": (
            "PUBLISH foo 1.0.0\n"
            "ADD foo ^2.0.0\n"
            "ADD foo ^3.0.0\n"
            "RESOLVE\n"
        ),
        "expected": "OK\nOK\nOK\nCONFLICT foo ^2.0.0",
    },
}


@pytest.fixture(scope="session")
def built_binary():
    """Compile the solver binary if not already present."""
    import os
    if not os.path.isfile(BIN[0]):
        subprocess.run(
            ["bash", "-c", "cd /app && go build -o /app/solver /app/solver.go"],
            capture_output=True, timeout=60,
        )
    return BIN[0]


@pytest.mark.parametrize("name", FIXTURES.keys())
def test_fixture(name, built_binary):
    """Run fixture through solver binary, compare stdout."""
    fx = FIXTURES[name]
    proc = subprocess.run(
        BIN,
        input=fx["input"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )
    actual = proc.stdout.strip()
    expected = fx["expected"].strip()
    assert actual == expected, (
        f"\n--- fixture: {name} ---\n"
        f"input:\n{fx['input']}\n"
        f"expected:\n{expected}\n"
        f"actual:\n{actual}"
    )
