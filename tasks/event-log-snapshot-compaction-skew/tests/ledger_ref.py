"""
Independent Python reference for ledger branch observations.

Mirrors the public contract in instruction.md and docs/report_schema.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


Leg = tuple[str, ...]


def _mix(acc: int, text: str) -> int:
    for byte in text.encode("utf-8"):
        acc ^= byte
        acc = (acc * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return acc


def hex16(value: int) -> str:
    if value == 0:
        value = 0xCBF29CE484222325
    return f"{value:016x}"


def hex64(value: int) -> str:
    if value == 0:
        value = 0xCBF29CE484222325
    hi = value ^ (value >> 32)
    return f"{hi:016x}{value:016x}"


@dataclass
class StagingMove:
    src: int
    dst: int
    amt: int


@dataclass
class Record:
    seq: int
    acct: int
    kind: str
    val: int
    step: int

    def as_line(self) -> str:
        return f"{self.seq:04}|{self.acct:03}|{self.kind}|{self.val}|{self.step:03}"


@dataclass
class Ledger:
    pots: dict[int, int] = field(default_factory=dict)
    retired: set[int] = field(default_factory=set)
    staging: list[StagingMove] = field(default_factory=list)
    stream: list[Record] = field(default_factory=list)
    seq: int = 0
    resumed: bool = False

    def bump(self, acct: int, kind: str, val: int, step: int) -> None:
        self.seq += 1
        self.stream.append(Record(self.seq, acct, kind, val, step))

    def flush_staging(self, step: int) -> None:
        moves = list(self.staging)
        self.staging.clear()
        for mv in moves:
            if mv.src in self.retired or mv.dst in self.retired:
                continue
            from_bal = self.pots.get(mv.src, 0)
            to_bal = self.pots.get(mv.dst, 0)
            self.pots[mv.src] = from_bal - mv.amt
            self.pots[mv.dst] = to_bal + mv.amt
            self.bump(mv.src, "xfer", -mv.amt, step)
            self.bump(mv.dst, "xfer", mv.amt, step)

    def apply_leg(self, step: int, leg: Leg) -> None:
        tag = leg[0]
        if tag == "open":
            acct, seed = int(leg[1]), int(leg[2])
            if acct in self.retired:
                return
            self.pots[acct] = seed
            self.bump(acct, "open", seed, step)
        elif tag == "move":
            src, dst, amt = int(leg[1]), int(leg[2]), int(leg[3])
            self.staging.append(StagingMove(src, dst, amt))
        elif tag == "retire":
            acct = int(leg[1])
            self.retired.add(acct)
            self.pots.pop(acct, None)
            self.bump(acct, "retire", 0, step)
        elif tag == "close":
            self.flush_staging(step)

    def end_step(self, step: int) -> None:
        if self.staging:
            self.flush_staging(step)

    def step_m(self, step: int, legs: list[Leg]) -> None:
        for leg in legs:
            self.apply_leg(step, leg)
        self.end_step(step)

    def aggregate_digest(self) -> str:
        acc = 0xCBF29CE484222325
        for acct in sorted(self.pots):
            acc = _mix(acc, f"{acct}:{self.pots[acct]};")
        acc = _mix(acc, f"r:{len(self.retired)};")
        return hex64(acc)

    def seq_high_water(self) -> int:
        return self.seq


@dataclass
class Scenario:
    name: str
    steps: int
    save_at: int
    checkpoint_leg: int
    resume_from: int
    compact_at: int
    pots: dict[int, int]
    batches: list[list[Leg]]

    def initial_state(self) -> Ledger:
        return Ledger(pots=dict(self.pots))

    def batch_at(self, step: int) -> list[Leg]:
        return self.batches[step % len(self.batches)]


def seal_v(state: Ledger) -> str:
    rows = sorted(state.pots.items())
    out = [f"v1|{state.seq}"]
    for acct, bal in rows:
        out.append(f"p,{acct},{bal}")
    for acct in sorted(state.retired):
        out.append(f"r,{acct}")
    for mv in state.staging:
        out.append(f"s,{mv.src},{mv.dst},{mv.amt}")
    return "\n".join(out) + "\n"


def raise_w(payload: str) -> Ledger:
    pots: dict[int, int] = {}
    retired: set[int] = set()
    staging: list[StagingMove] = []
    seq = 0
    for idx, line in enumerate(payload.splitlines()):
        if idx == 0:
            if line.startswith("v1|"):
                seq = int(line[3:] or "0")
            continue
        if not line.strip():
            continue
        parts = line.split(",")
        tag = parts[0]
        if tag == "p":
            pots[int(parts[1])] = int(parts[2])
        elif tag == "r":
            retired.add(int(parts[1]))
        elif tag == "s":
            staging.append(StagingMove(int(parts[1]), int(parts[2]), int(parts[3])))
    state = Ledger(pots=pots)
    state.retired = retired
    state.staging = staging
    state.seq = seq
    state.resumed = True
    return state


def fold_x(entries: list[Record], _retired: set[int]) -> list[Record]:
    return [Record(e.seq, e.acct, e.kind, e.val, e.step) for e in entries]


@dataclass
class Seen:
    live: set[tuple[int, int]] = field(default_factory=set)


def trace_y(state: Ledger, entry: Record, _resume: bool, seen: Seen) -> None:
    key = (entry.seq, entry.acct)
    if key in seen.live:
        return
    seen.live.add(key)
    if entry.kind == "open":
        state.pots[entry.acct] = entry.val
    elif entry.kind == "xfer":
        state.pots[entry.acct] = state.pots.get(entry.acct, 0) + entry.val
    elif entry.kind == "retire":
        state.retired.add(entry.acct)
        state.pots.pop(entry.acct, None)
    if entry.seq > state.seq:
        state.seq = entry.seq
    state.stream.append(
        Record(entry.seq, entry.acct, entry.kind, entry.val, entry.step)
    )


def stream_digest(records: list[Record]) -> str:
    acc = 0xCBF29CE484222325
    for record in records:
        acc = _mix(acc, record.as_line())
    return hex16(acc)


@dataclass
class BranchRecord:
    branch: str
    aggregate_digest: str
    event_digest: str
    seq_high_water: int
    entries: list[str]
    checkpoint_bytes: int
    fold_records: int


def finish(name: str, state: Ledger, checkpoint_bytes: int, fold_records: int) -> BranchRecord:
    return BranchRecord(
        branch=name,
        aggregate_digest=state.aggregate_digest(),
        event_digest=stream_digest(state.stream),
        seq_high_water=state.seq_high_water(),
        entries=[r.as_line() for r in state.stream],
        checkpoint_bytes=checkpoint_bytes,
        fold_records=fold_records,
    )


def apply_checkpoint_step(
    state: Ledger, case: Scenario, step: int, snap: list[str], snap_seq: list[int]
) -> None:
    legs = case.batch_at(step)
    for idx, leg in enumerate(legs):
        if idx == case.checkpoint_leg:
            snap[0] = seal_v(state)
            snap_seq[0] = state.seq
        state.apply_leg(step, leg)
    state.end_step(step)


def apply_resume_step(branch: Ledger, case: Scenario, step: int, snap: str) -> Ledger:
    legs = case.batch_at(step)
    for idx, leg in enumerate(legs):
        if idx == case.checkpoint_leg:
            restored = raise_w(snap)
            branch.pots = restored.pots
            branch.retired = restored.retired
            branch.staging = restored.staging
            branch.seq = restored.seq
            branch.resumed = True
            branch.step_m(step, legs[idx:])
            return branch
        branch.apply_leg(step, leg)
    branch.end_step(step)
    return branch


def continuous(case: Scenario) -> BranchRecord:
    state = case.initial_state()
    for step in range(case.steps):
        state.step_m(step, case.batch_at(step))
    return finish("continuous", state, 0, 0)


def crash_resume(case: Scenario) -> BranchRecord:
    probe = case.initial_state()
    snap = [""]
    snap_seq = [0]
    for step in range(case.resume_from + 1):
        if step == case.save_at:
            apply_checkpoint_step(probe, case, step, snap, snap_seq)
        else:
            probe.step_m(step, case.batch_at(step))
    branch = case.initial_state()
    for step in range(case.steps):
        if step < case.save_at:
            branch.step_m(step, case.batch_at(step))
        elif step == case.save_at:
            branch = apply_resume_step(branch, case, step, snap[0])
        else:
            branch.step_m(step, case.batch_at(step))
    return finish("crash_resume", branch, len(snap[0]), 0)


def compaction_replay(case: Scenario) -> BranchRecord:
    probe = case.initial_state()
    snap = [""]
    snap_seq = [0]
    for step in range(case.steps):
        if step == case.save_at:
            apply_checkpoint_step(probe, case, step, snap, snap_seq)
        else:
            probe.step_m(step, case.batch_at(step))
    tail = [
        Record(r.seq, r.acct, r.kind, r.val, r.step)
        for r in probe.stream
        if r.seq > snap_seq[0]
        and r.step > case.save_at
        and r.step <= case.compact_at
    ]
    folded = fold_x(tail, probe.retired)
    branch = case.initial_state()
    for step in range(case.save_at):
        branch.step_m(step, case.batch_at(step))
    branch = apply_resume_step(branch, case, case.save_at, snap[0])
    seen = Seen()
    for entry in folded:
        trace_y(branch, entry, True, seen)
    for step in range(case.compact_at + 1, case.steps):
        branch.step_m(step, case.batch_at(step))
    return finish("compaction_replay", branch, len(snap[0]), len(folded))


def reference_run(case: Scenario) -> dict[str, BranchRecord]:
    return {
        "continuous": continuous(case),
        "crash_resume": crash_resume(case),
        "compaction_replay": compaction_replay(case),
    }


def reference_report(cases: list[Scenario]) -> dict[str, object]:
    runs = []
    for case in cases:
        branches = reference_run(case)
        seq_hw = max(b.seq_high_water for b in branches.values())
        runs.append(
            {
                "scenario": case.name,
                "seq_high_water": seq_hw,
                "branches": [
                    {
                        "branch": b.branch,
                        "aggregate_digest": b.aggregate_digest,
                        "event_digest": b.event_digest,
                        "seq_high_water": b.seq_high_water,
                        "checkpoint_bytes": b.checkpoint_bytes,
                        "fold_records": b.fold_records,
                        "entries": b.entries,
                    }
                    for b in (
                        branches["continuous"],
                        branches["crash_resume"],
                        branches["compaction_replay"],
                    )
                ],
            }
        )
    return {"report_version": 1, "runs": runs}


def bundled_cases() -> list[Scenario]:
    """Scenario definitions aligned with environment/src/sim/case.rs bundled set."""
    return _core_bundled_cases()


def probe_cases() -> list[Scenario]:
    """Probe-only canaries exercised by divergence and reference checks."""
    return [
        Scenario(
            name="quartz_ledger_skew",
            steps=15,
            save_at=3,
            checkpoint_leg=0,
            resume_from=10,
            compact_at=8,
            pots={4: 100, 18: 60},
            batches=[
                [("open", "27", "40"), ("move", "4", "27", "15"), ("close",)],
                [("move", "18", "27", "10"), ("close",)],
                [("move", "4", "18", "12"), ("move", "27", "4", "5"), ("close",)],
                [("move", "18", "27", "8"), ("move", "4", "27", "6"), ("close",)],
                [("retire", "27"), ("move", "18", "4", "9"), ("close",)],
                [("open", "36", "30"), ("move", "4", "36", "11"), ("close",)],
                [("move", "36", "18", "7"), ("close",)],
            ],
        ),
        Scenario(
            name="obsidian_tail_fold",
            steps=19,
            save_at=4,
            checkpoint_leg=2,
            resume_from=14,
            compact_at=10,
            pots={2: 150, 20: 90},
            batches=[
                [("open", "25", "55"), ("move", "2", "25", "20"), ("close",)],
                [("move", "20", "25", "14"), ("close",)],
                [("open", "39", "45"), ("move", "25", "39", "18"), ("move", "2", "39", "9"), ("close",)],
                [("move", "39", "20", "11"), ("close",)],
                [
                    ("move", "20", "39", "8"),
                    ("move", "2", "25", "10"),
                    ("move", "39", "2", "6"),
                    ("close",),
                ],
                [("retire", "25"), ("move", "39", "20", "5"), ("close",)],
                [("open", "48", "35"), ("move", "2", "48", "13"), ("close",)],
                [("move", "48", "39", "9"), ("move", "20", "48", "8"), ("close",)],
                [("retire", "39"), ("move", "48", "2", "6"), ("close",)],
            ],
        ),
    ]


def _core_bundled_cases() -> list[Scenario]:
    return [
        Scenario(
            name="copper_wire_fan",
            steps=14,
            save_at=4,
            checkpoint_leg=1,
            resume_from=9,
            compact_at=10,
            pots={11: 120, 19: 80},
            batches=[
                [("open", "31", "50"), ("move", "11", "31", "20"), ("move", "19", "31", "10"), ("close",)],
                [("move", "31", "11", "5"), ("close",)],
                [("open", "44", "30"), ("move", "31", "44", "15"), ("close",)],
                [("move", "44", "19", "8"), ("close",)],
                [("move", "11", "44", "12"), ("move", "19", "31", "6"), ("close",)],
                [("retire", "31"), ("move", "44", "11", "4"), ("close",)],
                [("open", "52", "25"), ("move", "11", "52", "10"), ("close",)],
            ],
        ),
        Scenario(
            name="nickel_merge_lane",
            steps=16,
            save_at=5,
            checkpoint_leg=1,
            resume_from=11,
            compact_at=12,
            pots={7: 200, 13: 150},
            batches=[
                [("open", "21", "40"), ("move", "7", "21", "25"), ("close",)],
                [("move", "13", "21", "15"), ("move", "21", "7", "5"), ("close",)],
                [("open", "28", "60"), ("move", "7", "28", "30"), ("close",)],
                [("move", "28", "13", "12"), ("close",)],
                [("move", "7", "28", "8"), ("move", "13", "21", "10"), ("close",)],
                [("retire", "21"), ("move", "28", "7", "20"), ("close",)],
                [("move", "13", "28", "7"), ("close",)],
                [("open", "35", "45"), ("move", "28", "35", "15"), ("close",)],
            ],
        ),
        Scenario(
            name="slate_purge_arc",
            steps=18,
            save_at=6,
            checkpoint_leg=1,
            resume_from=12,
            compact_at=14,
            pots={5: 90, 9: 110, 14: 70},
            batches=[
                [("open", "22", "55"), ("move", "5", "22", "20"), ("close",)],
                [("move", "9", "22", "18"), ("close",)],
                [("move", "14", "22", "12"), ("move", "22", "5", "8"), ("close",)],
                [("retire", "22"), ("move", "9", "14", "6"), ("close",)],
                [("open", "33", "40"), ("move", "5", "33", "15"), ("close",)],
                [("move", "14", "33", "10"), ("move", "33", "9", "5"), ("close",)],
                [("retire", "33"), ("move", "5", "14", "12"), ("close",)],
                [("open", "41", "35"), ("move", "9", "41", "20"), ("close",)],
            ],
        ),
        Scenario(
            name="brass_split_ladder",
            steps=20,
            save_at=7,
            checkpoint_leg=1,
            resume_from=15,
            compact_at=16,
            pots={3: 160, 8: 140, 12: 100},
            batches=[
                [("open", "17", "75"), ("move", "3", "17", "30"), ("close",)],
                [("move", "8", "17", "20"), ("close",)],
                [("open", "24", "50"), ("move", "12", "24", "25"), ("move", "17", "24", "10"), ("close",)],
                [("move", "24", "3", "15"), ("close",)],
                [("move", "8", "12", "18"), ("move", "3", "24", "12"), ("close",)],
                [("retire", "17"), ("move", "24", "8", "14"), ("close",)],
                [("open", "29", "65"), ("move", "12", "29", "22"), ("close",)],
                [("move", "29", "3", "9"), ("move", "8", "29", "11"), ("close",)],
                [("retire", "24"), ("move", "29", "12", "8"), ("close",)],
            ],
        ),
        Scenario(
            name="iron_cross_weave",
            steps=17,
            save_at=2,
            checkpoint_leg=2,
            resume_from=10,
            compact_at=8,
            pots={6: 130, 15: 95},
            batches=[
                [("open", "26", "45"), ("move", "6", "26", "18"), ("close",)],
                [("move", "15", "26", "12"), ("close",)],
                [("open", "38", "35"), ("move", "26", "38", "10"), ("move", "6", "38", "8"), ("close",)],
                [("close",), ("move", "38", "15", "6"), ("close",)],
                [("retire", "26"), ("move", "38", "6", "14"), ("close",)],
                [("open", "47", "28"), ("move", "15", "47", "9"), ("close",)],
                [("move", "6", "47", "11"), ("move", "38", "15", "5"), ("close",)],
                [("retire", "38"), ("move", "47", "6", "7"), ("close",)],
            ],
        ),
        Scenario(
            name="mercury_gate_fold",
            steps=16,
            save_at=5,
            checkpoint_leg=1,
            resume_from=12,
            compact_at=11,
            pots={10: 180, 16: 120},
            batches=[
                [("open", "30", "50"), ("move", "10", "30", "25"), ("close",)],
                [("move", "16", "30", "15"), ("close",)],
                [("open", "42", "40"), ("move", "30", "42", "20"), ("close",)],
                [("move", "42", "10", "12"), ("close",)],
                [("move", "10", "42", "8"), ("move", "16", "30", "10"), ("close",)],
                [("retire", "30"), ("move", "42", "16", "6"), ("close",)],
                [("open", "55", "35"), ("move", "10", "55", "14"), ("close",)],
                [("move", "55", "42", "9"), ("move", "42", "10", "5"), ("close",)],
            ],
        ),
    ]


def parse_entry_line(line: str) -> Record:
    seq_s, acct_s, kind, val_s, step_s = line.split("|", 4)
    return Record(int(seq_s), int(acct_s), kind, int(val_s), int(step_s))


def recompute_event_digest(entries: list[str]) -> str:
    records = [parse_entry_line(line) for line in entries]
    return stream_digest(records)


def replay_entries_to_ledger(case: Scenario, entries: list[str]) -> Ledger:
    state = case.initial_state()
    seen = Seen()
    for line in entries:
        trace_y(state, parse_entry_line(line), False, seen)
    return state


def recompute_aggregate_digest(case: Scenario, entries: list[str]) -> str:
    return replay_entries_to_ledger(case, entries).aggregate_digest()


def entry_seq_high_water(entries: list[str]) -> int:
    if not entries:
        return 0
    return max(parse_entry_line(line).seq for line in entries)


def replay_pot_map(case: Scenario, entries: list[str]) -> dict[int, int]:
    return replay_entries_to_ledger(case, entries).pots


def replay_retired_set(case: Scenario, entries: list[str]) -> set[int]:
    return replay_entries_to_ledger(case, entries).retired


def reference_checkpoint_bytes(case: Scenario) -> int:
    return reference_run(case)["crash_resume"].checkpoint_bytes


def xfer_steps_balance_neutral(entries: list[str]) -> bool:
    """Each step's xfer legs sum to zero (paired move semantics)."""
    by_step: dict[int, list[int]] = {}
    for line in entries:
        seq_s, _acct, kind, val_s, step_s = line.split("|", 4)
        if kind != "xfer":
            continue
        by_step.setdefault(int(step_s), []).append(int(val_s))
    for vals in by_step.values():
        if sum(vals) != 0:
            return False
    return True
