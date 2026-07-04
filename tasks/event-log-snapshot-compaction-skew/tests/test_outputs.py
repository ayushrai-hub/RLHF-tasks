"""Verifier for deterministic branch observations."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ledger_ref import (
    bundled_cases,
    probe_cases,
    reference_checkpoint_bytes,
    reference_report,
    replay_pot_map,
    replay_retired_set,
    xfer_steps_balance_neutral,
)

APP = Path("/app/environment")
OUT = Path("/app/output/ledger_report.json")
BRANCHES = {"continuous", "crash_resume", "compaction_replay"}
SCENARIOS = {case.name for case in bundled_cases()}
PROBE_SCENARIOS = {case.name for case in probe_cases()}
ALL_SCENARIOS = sorted(SCENARIOS | PROBE_SCENARIOS)


def _read_json(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _bundle_meta() -> dict[str, dict[str, int]]:
    current: str | None = None
    out: dict[str, dict[str, int]] = {}
    for line in (APP / "config" / "bundles.toml").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("[bundles.") and stripped.endswith("]"):
            current = stripped[len("[bundles.") : -1]
            if current not in {"count", "profile"}:
                out[current] = {}
            continue
        if current is None or current not in out or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key in {"steps", "save_at", "compact_at", "checkpoint_leg", "resume_from"}:
            out[current][key] = int(value.strip())
    return out


def _parse_entry(line: str) -> tuple[int, int, str, int, int]:
    seq_s, acct_s, kind, val_s, step_s = line.split("|", 4)
    return int(seq_s), int(acct_s), kind, int(val_s), int(step_s)


def _tail_window_lines(entries: list[str], save_at: int, compact_at: int) -> list[str]:
    return [line for line in entries if save_at < _parse_entry(line)[4] <= compact_at]


def _seqs_strictly_increasing(entries: list[str]) -> bool:
    last = 0
    for line in entries:
        seq = _parse_entry(line)[0]
        if seq <= last:
            return False
        last = seq
    return True


def _no_duplicate_seq_acct(entries: list[str]) -> bool:
    seen: set[tuple[int, int]] = set()
    for line in entries:
        seq, acct, _kind, _val, _step = _parse_entry(line)
        key = (seq, acct)
        if key in seen:
            return False
        seen.add(key)
    return True


def _compaction_fold_lines_within_window(
    continuous: list[str],
    compaction: list[str],
    save_at: int,
    compact_at: int,
) -> bool:
    tail = _tail_window_lines(continuous, save_at, compact_at)
    if not tail:
        return True
    pos = 0
    for line in compaction:
        step = _parse_entry(line)[4]
        if not (save_at < step <= compact_at):
            continue
        if pos >= len(tail) or line != tail[pos]:
            return False
        pos += 1
    return pos == len(tail)


def _is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    pos = 0
    for line in haystack:
        if pos < len(needle) and line == needle[pos]:
            pos += 1
    return pos == len(needle)


def _run_report() -> dict[str, object]:
    OUT.unlink(missing_ok=True)
    completed = subprocess.run(
        ["bash", "/app/environment/tools/run_matrix.sh"],
        cwd="/app",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert OUT.is_file(), "report was not regenerated"
    return _read_json(OUT)


def _run_subset(scenarios: str) -> dict[str, object]:
    OUT.unlink(missing_ok=True)
    completed = subprocess.run(
        ["bash", "/app/environment/tools/run_subset.sh", scenarios],
        cwd="/app",
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert OUT.is_file(), "report was not regenerated"
    return _read_json(OUT)


def _branch_map(run: dict[str, object]) -> dict[str, dict[str, object]]:
    branches = run.get("branches")
    assert isinstance(branches, list)
    mapped: dict[str, dict[str, object]] = {}
    for branch in branches:
        assert isinstance(branch, dict)
        name = branch.get("branch")
        assert isinstance(name, str)
        mapped[name] = branch
    return mapped


def _assert_branch_matches_reference(
    got: dict[str, object],
    expected: dict[str, object],
    scenario: str,
    branch_name: str,
) -> None:
    for key in (
        "aggregate_digest",
        "event_digest",
        "seq_high_water",
        "entries",
        "checkpoint_bytes",
        "fold_records",
    ):
        assert got.get(key) == expected.get(key), f"{scenario}/{branch_name}/{key}"


def _branch_record_dict(branch: object) -> dict[str, object]:
    return {
        "aggregate_digest": branch.aggregate_digest,  # type: ignore[attr-defined]
        "event_digest": branch.event_digest,  # type: ignore[attr-defined]
        "seq_high_water": branch.seq_high_water,  # type: ignore[attr-defined]
        "entries": branch.entries,  # type: ignore[attr-defined]
        "checkpoint_bytes": branch.checkpoint_bytes,  # type: ignore[attr-defined]
        "fold_records": branch.fold_records,  # type: ignore[attr-defined]
    }


def test_z01_reference_oracle_matches_all_branches() -> None:
    """Independent reference simulation must match every branch observation."""
    from ledger_ref import reference_run

    payload = _run_report()
    expected = reference_report(bundled_cases())
    assert payload.get("report_version") == expected["report_version"]
    runs = payload.get("runs")
    assert isinstance(runs, list)
    assert len(runs) == len(bundled_cases())
    for run, case in zip(runs, bundled_cases(), strict=True):
        assert isinstance(run, dict)
        assert run.get("scenario") == case.name
        ref = reference_run(case)
        branches = _branch_map(run)
        for name in BRANCHES:
            _assert_branch_matches_reference(
                branches[name],
                _branch_record_dict(ref[name]),
                case.name,
                name,
            )


def test_z02_compaction_replay_stream_matches_continuous() -> None:
    """Compaction replay must emit the same durable stream as the uninterrupted path."""
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        branches = _branch_map(run)
        continuous = branches["continuous"]["entries"]
        compaction = branches["compaction_replay"]["entries"]
        assert isinstance(continuous, list)
        assert isinstance(compaction, list)
        assert compaction == continuous, scenario


def test_z03_forced_branches_share_reference_checkpoint_bytes() -> None:
    """Forced branches must seal the same checkpoint payload length as the reference."""
    from ledger_ref import reference_run

    by_name = {case.name: case for case in bundled_cases()}
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        case = by_name[scenario]
        expected = reference_checkpoint_bytes(case)
        branches = _branch_map(run)
        crash_bytes = branches["crash_resume"]["checkpoint_bytes"]
        compaction_bytes = branches["compaction_replay"]["checkpoint_bytes"]
        assert branches["continuous"]["checkpoint_bytes"] == 0, scenario
        assert expected > 0, scenario
        assert crash_bytes == expected, scenario
        assert compaction_bytes == expected, scenario
        ref = reference_run(case)
        assert crash_bytes == ref["crash_resume"].checkpoint_bytes, scenario
        assert compaction_bytes == ref["compaction_replay"].checkpoint_bytes, scenario


def test_z04_generation_is_byte_stable_across_triple_run() -> None:
    """Three consecutive matrix runs must emit byte-identical report content."""
    blobs: list[bytes] = []
    for _ in range(3):
        _run_report()
        with OUT.open("rb") as handle:
            blobs.append(handle.read())
    assert blobs[0] == blobs[1] == blobs[2]
    first = _read_json(OUT)
    _run_report()
    second = _read_json(OUT)
    assert second == first


def test_z05_sequence_subsets_align_with_reference() -> None:
    """Declared scenario subsets must match the independent reference on every branch."""
    from ledger_ref import reference_run

    sequences = _read_json(APP / "ci" / "sequences.json")["sequences"]
    for sequence in sequences:
        scenario_list = sequence["scenarios"]
        assert isinstance(scenario_list, list)
        payload = _run_subset(",".join(scenario_list))
        runs = payload["runs"]
        assert isinstance(runs, list)
        assert len(runs) == len(scenario_list)
        observed = [run["scenario"] for run in runs if isinstance(run, dict)]
        assert observed == scenario_list
        by_name = {case.name: case for case in bundled_cases()}
        for run in runs:
            assert isinstance(run, dict)
            scenario = str(run["scenario"])
            case = by_name[scenario]
            ref = reference_run(case)
            branches = _branch_map(run)
            for name in BRANCHES:
                _assert_branch_matches_reference(
                    branches[name],
                    _branch_record_dict(ref[name]),
                    scenario,
                    name,
                )


def test_z06_subsystem_regressions_trap_partial_fixes() -> None:
    """Each known-bad subsystem snapshot must diverge on its targeted scenario probe."""
    subprocess.run(
        ["bash", "/app/environment/ci/matrix_regress.sh"],
        cwd="/app",
        check=True,
    )


def test_z07_crash_resume_full_stream_matches_continuous() -> None:
    """Crash resume must rebuild the same durable stream as the uninterrupted path."""
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        branches = _branch_map(run)
        continuous = branches["continuous"]["entries"]
        crash = branches["crash_resume"]["entries"]
        assert isinstance(continuous, list)
        assert isinstance(crash, list)
        assert crash == continuous, scenario


def test_z08_compaction_tail_lines_keep_continuous_order() -> None:
    """Folded compaction tails must preserve continuous-stream line order inside the window."""
    meta = _bundle_meta()
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        timing = meta[scenario]
        branches = _branch_map(run)
        tail_lines = _tail_window_lines(
            branches["continuous"]["entries"],
            timing["save_at"],
            timing["compact_at"],
        )
        assert _is_subsequence(tail_lines, branches["compaction_replay"]["entries"]), scenario


def test_z09_xfer_steps_balance_neutral_on_every_branch() -> None:
    """Xfer legs recorded within a step must sum to zero on every branch stream."""
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        branches = _branch_map(run)
        for name in BRANCHES:
            entries = branches[name]["entries"]
            assert isinstance(entries, list)
            assert xfer_steps_balance_neutral(entries), f"{scenario}/{name}"


def test_z10_double_fold_idempotent_on_all_scenarios() -> None:
    """Re-applying folded compaction tails must stay idempotent on every scenario."""
    _run_report()
    for scenario in ALL_SCENARIOS:
        subprocess.run(
            ["bash", "/app/environment/tools/double_fold_probe.sh", scenario],
            cwd="/app",
            check=True,
        )


def test_z11_orphan_checkpoint_ignored_on_all_scenarios() -> None:
    """Unrecognized checkpoint seal lines must not poison restoration on every scenario."""
    _run_report()
    for scenario in ALL_SCENARIOS:
        subprocess.run(
            ["bash", "/app/environment/tools/orphan_checkpoint_probe.sh", scenario],
            cwd="/app",
            check=True,
        )


def test_z12_staging_checkpoint_roundtrip_on_all_scenarios() -> None:
    """Mid-batch checkpoint seals must round-trip staged state on every scenario."""
    _run_report()
    for scenario in ALL_SCENARIOS:
        subprocess.run(
            ["bash", "/app/environment/tools/staging_roundtrip.sh", scenario],
            cwd="/app",
            check=True,
        )


def test_z13_branch_probes_align_after_regeneration() -> None:
    """Per-scenario branch alignment probes must pass after report regeneration."""
    _run_report()
    for scenario in ALL_SCENARIOS:
        subprocess.run(
            ["bash", "/app/environment/tools/divergence_probe.sh", scenario],
            cwd="/app",
            check=True,
        )


def test_z14_replayed_pot_balances_match_across_branches() -> None:
    """Independent replay from each branch stream must converge on the same pot map."""
    by_name = {case.name: case for case in bundled_cases()}
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        case = by_name[scenario]
        branches = _branch_map(run)
        pots = {
            name: replay_pot_map(case, branches[name]["entries"])
            for name in BRANCHES
        }
        continuous_pots = pots["continuous"]
        for name in ("crash_resume", "compaction_replay"):
            assert pots[name] == continuous_pots, f"{scenario}/{name}"


def test_z15_replayed_retired_sets_match_across_branches() -> None:
    """Independent replay from each branch stream must converge on the same retired keys."""
    by_name = {case.name: case for case in bundled_cases()}
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        case = by_name[scenario]
        branches = _branch_map(run)
        retired = {
            name: replay_retired_set(case, branches[name]["entries"])
            for name in BRANCHES
        }
        continuous_retired = retired["continuous"]
        for name in ("crash_resume", "compaction_replay"):
            assert retired[name] == continuous_retired, f"{scenario}/{name}"


def test_z16_branch_entry_counts_match_continuous() -> None:
    """Every forced branch must record the same number of durable lines as continuous."""
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        branches = _branch_map(run)
        continuous_count = len(branches["continuous"]["entries"])
        for name in ("crash_resume", "compaction_replay"):
            assert len(branches[name]["entries"]) == continuous_count, f"{scenario}/{name}"


def test_z17_probe_canaries_match_reference() -> None:
    """Probe-only canaries must match the independent reference on every branch observation."""
    from ledger_ref import reference_run

    by_name = {case.name: case for case in probe_cases()}
    for case in probe_cases():
        payload = _run_subset(case.name)
        runs = payload["runs"]
        assert isinstance(runs, list)
        assert len(runs) == 1
        run = runs[0]
        assert isinstance(run, dict)
        assert run.get("scenario") == case.name
        ref = reference_run(by_name[case.name])
        branches = _branch_map(run)
        for name in BRANCHES:
            _assert_branch_matches_reference(
                branches[name],
                _branch_record_dict(ref[name]),
                case.name,
                name,
            )


def test_z18_compaction_fold_lines_respect_step_window() -> None:
    """Compaction replay must replay folded tail lines exactly inside (save_at, compact_at]."""
    meta = _bundle_meta()
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        timing = meta[scenario]
        branches = _branch_map(run)
        assert _compaction_fold_lines_within_window(
            branches["continuous"]["entries"],
            branches["compaction_replay"]["entries"],
            timing["save_at"],
            timing["compact_at"],
        ), scenario


def test_z19_entry_streams_are_strictly_monotonic() -> None:
    """Every branch stream must use strictly increasing sequence numbers without (seq, acct) duplicates."""
    payload = _run_report()
    for run in payload["runs"]:
        scenario = str(run["scenario"])
        for name in BRANCHES:
            entries = _branch_map(run)[name]["entries"]
            assert isinstance(entries, list)
            assert _seqs_strictly_increasing(entries), f"{scenario}/{name}"
            assert _no_duplicate_seq_acct(entries), f"{scenario}/{name}"


def test_z20_probe_canaries_replayed_state_matches_continuous() -> None:
    """Probe scenarios must show identical replayed pot and retired state on every branch."""
    by_name = {case.name: case for case in probe_cases()}
    for case in probe_cases():
        payload = _run_subset(case.name)
        run = payload["runs"][0]
        assert isinstance(run, dict)
        branches = _branch_map(run)
        scenario = case.name
        ref_case = by_name[scenario]
        pots = {
            name: replay_pot_map(ref_case, branches[name]["entries"])
            for name in BRANCHES
        }
        retired = {
            name: replay_retired_set(ref_case, branches[name]["entries"])
            for name in BRANCHES
        }
        for name in ("crash_resume", "compaction_replay"):
            assert pots[name] == pots["continuous"], f"{scenario}/{name}/pots"
            assert retired[name] == retired["continuous"], f"{scenario}/{name}/retired"
            assert branches[name]["entries"] == branches["continuous"]["entries"], scenario
