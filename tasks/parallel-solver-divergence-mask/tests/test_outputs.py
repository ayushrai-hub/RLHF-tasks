"""C++ acceptance gates for tb_iter.

Each pytest case runs one named gate from the hidden C++ verifier under
/tests/verifier. The reference oracle and behavioral assertions live in C++,
not Python. A single wrong fold_token string, checkpoint mismatch, or worker
drift fails the gate.
"""

import subprocess
from pathlib import Path

import pytest

BUILT_BIN = Path("/app/build/tb_iter")
VERIFIER_BUILD = Path("/tmp/tb3-verifier-build")
VERIFIER_BIN = VERIFIER_BUILD / "tb_iter_verifier"

GATES = (
    "rebuild_agent_binary",
    "cases_csv_immutable",
    "worker_antipode_blob_lock",
    "parallel_full_contract_worker_sweep",
    "fold_token_exact_precision_sweep",
    "weight_pre_renorm_precision_seeds",
    "objective_cross_worker_invariance",
    "audit_chain_antipode_lock",
    "continue_fresh_parity_with_journal",
    "journal_eight_hop_phase_ladder",
    "journal_mid_chain_worker_mismatch_rejects",
    "journal_corrupt_tail_rejects_continue",
    "journal_invalid_tail_fields_rejects",
    "journal_seed_tail_mismatch_rejects",
    "checkpoint_precision_roundtrip",
    "save_continue_triple_hop_fold_lock",
    "worker_sweep_audit_invariant_with_journal",
    "layout_dual_flag_invariance",
    "runtime_validation_matrix",
    "continued_report_neutral_parity",
    "dispersion_objective_formula_grid",
)


@pytest.fixture(scope="session", autouse=True)
def _rebuild_from_source() -> None:
    subprocess.run(
        "rm -rf /app/build && "
        "cmake -S /app/environment -B /app/build -DCMAKE_BUILD_TYPE=Release && "
        "cmake --build /app/build --parallel 1 && "
        "cp /app/build/tb_iter /usr/local/bin/tb_iter",
        shell=True,
        check=True,
    )
    assert BUILT_BIN.is_file()


@pytest.fixture(scope="session", autouse=True)
def _build_verifier() -> None:
    subprocess.run(
        [
            "cmake",
            "-S",
            "/tests/verifier",
            "-B",
            str(VERIFIER_BUILD),
            "-DCMAKE_BUILD_TYPE=Release",
        ],
        check=True,
    )
    subprocess.run(
        ["cmake", "--build", str(VERIFIER_BUILD), "--parallel", "1"],
        check=True,
    )
    assert VERIFIER_BIN.is_file()


def _run_gate(name: str) -> None:
    proc = subprocess.run(
        [str(VERIFIER_BIN), name],
        text=True,
        capture_output=True,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, (
        f"tb_iter_verifier gate {name} failed (rc={proc.returncode})\n"
        f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )


@pytest.mark.parametrize("gate", GATES)
def test_acceptance_gate(gate: str) -> None:
    """Each gate runs one C++ behavioral contract check against rebuilt tb_iter."""
    _run_gate(gate)
