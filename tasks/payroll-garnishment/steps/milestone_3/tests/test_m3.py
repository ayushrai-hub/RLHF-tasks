"""Milestone 3 tests: the per-order gross-up remittance run and the HMAC audit
chain."""
import base64
import hashlib
import hmac
import json
import os
import shutil
import subprocess

import pytest

APP_DIR = "/app"
BINARY = "/app/pay"
DATA_DIR = "/app/data"
SECRET = "pay-audit-key"
GENESIS = "0" * 64
MIN_WAGE_30X = 21750
POOL_CAP = 200000
BRACKETS = [(0, 0), (50000, 10), (200000, 22), (500000, 32)]


@pytest.fixture(scope="module", autouse=True)
def build_binary():
    result = subprocess.run(
        ["go", "build", "-o", BINARY, "."],
        cwd=APP_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"go build failed:\n{result.stderr}")


@pytest.fixture()
def fresh_db():
    backup = DATA_DIR + "_bak_m3"
    existed = os.path.isdir(DATA_DIR)
    if existed:
        if os.path.isdir(backup):
            shutil.rmtree(backup)
        shutil.move(DATA_DIR, backup)
    os.makedirs(DATA_DIR, exist_ok=True)
    yield
    shutil.rmtree(DATA_DIR, ignore_errors=True)
    if existed and os.path.isdir(backup):
        shutil.move(backup, DATA_DIR)


# ---- reference gross-up engine (mirror of milestone two) -------------------

def ref_round(num, den):
    q, r = divmod(num, den)
    twice = r * 2
    if twice > den or (twice == den and q % 2 == 1):
        q += 1
    return q


def ref_tax(gross):
    if gross <= 0:
        return 0
    acc = 0
    for i, (thr, rate) in enumerate(BRACKETS):
        nxt = BRACKETS[i + 1][0] if i + 1 < len(BRACKETS) else None
        if gross <= thr:
            break
        top = gross if (nxt is None or gross < nxt) else nxt
        acc += (top - thr) * rate
    return ref_round(acc, 100)


def ref_pool(disposable):
    if disposable <= 0:
        return 0
    p25 = ref_round(disposable * 25, 100)
    floor30 = max(disposable - MIN_WAGE_30X, 0)
    pool = min(p25, floor30)
    if pool > POOL_CAP:
        pool = POOL_CAP
    return pool


def ref_net(gross):
    disp = gross - ref_tax(gross)
    if disp < 0:
        disp = 0
    return disp - ref_pool(disp)


def ref_grossup(target):
    if target <= 0:
        return 0
    lo = target
    hi = target * 4
    guard = 0
    while ref_net(hi) < target and guard < 100:
        hi *= 2
        guard += 1
    it = 0
    while lo < hi and it < 200:
        mid = (lo + hi) // 2
        if ref_net(mid) >= target:
            hi = mid
        else:
            lo = mid + 1
        it += 1
    return lo


def entry_hash(seq, emp_id, order_id, kind, amount, prev):
    msg = f"{seq}|{emp_id}|{order_id}|{kind}|{amount}|{prev}"
    return hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()


def run(args):
    return subprocess.run([BINARY] + list(args), capture_output=True, text=True)


def init_db():
    assert run(["init"]).returncode == 0


def add_employee(name, gross, mandatory):
    assert run(["add-employee", name, "--gross", str(gross),
                "--mandatory", str(mandatory)]).returncode == 0


def add_order(emp, kind, priority, cap):
    r = run(["add-order", emp, "--kind", kind, "--priority", str(priority), "--cap", str(cap)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


def parse_lines(text):
    """Parse the per-order remit lines: [(oid, kind, amt)...]."""
    out = []
    for ln in text.strip().splitlines():
        if not ln.strip():
            continue
        parts = ln.split()
        out.append((int(parts[0]), parts[1], int(parts[2])))
    return out


def remit(emp):
    r = run(["remit", emp])
    assert r.returncode == 0, r.stderr
    return parse_lines(r.stdout)


class TestMilestone3:
    def test_remit_grossup_per_order(self, fresh_db):
        init_db()
        add_employee("alice", 999999, 0)
        cs = add_order("alice", "child_support", 1, 100000)
        cr = add_order("alice", "creditor", 2, 150000)
        got = remit("alice")
        assert got == [
            (cs, "child_support", ref_grossup(100000)),
            (cr, "creditor", ref_grossup(150000)),
        ]

    def test_remit_alloc_order_priority_then_id(self, fresh_db):
        init_db()
        add_employee("bob", 999999, 0)
        # add a priority-2 order before a priority-1 order; remit orders by
        # ascending priority then id.
        b = add_order("bob", "creditor", 2, 80000)
        a = add_order("bob", "child_support", 1, 120000)
        got = remit("bob")
        assert [g[0] for g in got] == [a, b]

    def test_remit_unknown_not_found(self, fresh_db):
        init_db()
        r = run(["remit", "ghost"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_remit_no_orders_empty(self, fresh_db):
        init_db()
        add_employee("solo", 200000, 0)
        r = run(["remit", "solo"])
        assert r.returncode == 0
        assert [ln for ln in r.stdout.strip().splitlines() if ln.strip()] == []

    def test_audit_chain_recompute(self, fresh_db):
        init_db()
        add_employee("alice", 999999, 0)
        cs = add_order("alice", "child_support", 1, 100000)
        cr = add_order("alice", "creditor", 2, 150000)
        lines = remit("alice")
        assert lines == [
            (cs, "child_support", ref_grossup(100000)),
            (cr, "creditor", ref_grossup(150000)),
        ]
        r = run(["audit"])
        rows = [ln.split() for ln in r.stdout.strip().splitlines() if ln.strip()]
        assert len(rows) == len(lines) == 2
        prev = GENESIS
        for i, (oid, kind, amt) in enumerate(lines, start=1):
            h = entry_hash(i, 1, oid, kind, amt, prev)
            assert rows[i - 1] == [str(i), "1", str(oid), kind, str(amt), h]
            prev = h

    def test_remit_append_only(self, fresh_db):
        """Two remit runs on the same db accumulate one continuous chain: the
        second run keeps counting the seq instead of restarting at 1, its first
        entry chains off the last hash of the first run, and audit-verify still
        reports the whole accumulated chain valid. A wipe-and-restart or a
        genesis-reset implementation fails this."""
        init_db()
        add_employee("alice", 999999, 0)
        cs = add_order("alice", "child_support", 1, 100000)
        cr = add_order("alice", "creditor", 2, 150000)
        amt_cs = ref_grossup(100000)
        amt_cr = ref_grossup(150000)
        # Run one writes seq 1 and 2, run two must append seq 3 and 4.
        remit("alice")
        remit("alice")
        r = run(["audit"])
        rows = [ln.split() for ln in r.stdout.strip().splitlines() if ln.strip()]
        assert len(rows) == 4
        # (a) the second run continues the counter rather than restarting at 1.
        assert [int(row[0]) for row in rows] == [1, 2, 3, 4]
        # Recompute the full four-entry chain with real prev-hash linkage across
        # the run boundary. A second remit that resets prev_hash to genesis (or
        # wipes the journal) produces a different hash for seq 3 and fails here.
        specs = [
            (cs, "child_support", amt_cs),
            (cr, "creditor", amt_cr),
            (cs, "child_support", amt_cs),
            (cr, "creditor", amt_cr),
        ]
        prev = GENESIS
        hashes = []
        for i, (oid, kind, amt) in enumerate(specs, start=1):
            h = entry_hash(i, 1, oid, kind, amt, prev)
            assert rows[i - 1] == [str(i), "1", str(oid), kind, str(amt), h]
            hashes.append(h)
            prev = h
        # (b) the first entry of run two (seq 3) chains off the last hash of run
        # one (seq 2): recomputing seq 3 with that hash as prev reproduces the
        # stored entry hash.
        run2_first = entry_hash(3, 1, cs, "child_support", amt_cs, hashes[1])
        assert rows[2][5] == run2_first
        # (c) the accumulated chain verifies end to end.
        v = run(["audit-verify"])
        assert v.returncode == 0
        assert v.stdout.strip() == "valid"

    def test_audit_verify_valid(self, fresh_db):
        init_db()
        add_employee("alice", 999999, 0)
        add_order("alice", "child_support", 1, 100000)
        remit("alice")
        r = run(["audit-verify"])
        assert r.returncode == 0
        assert r.stdout.strip() == "valid"

    def test_audit_secret_override(self, fresh_db):
        """The audit HMAC key honors PAY_AUDIT_SECRET instead of the default,
        so the stored entry hash differs from a default-key computation."""
        custom = "rotated-secret-9"
        env = dict(os.environ, PAY_AUDIT_SECRET=custom)

        def run_env(args):
            return subprocess.run([BINARY] + list(args), capture_output=True,
                                  text=True, env=env)

        assert run_env(["init"]).returncode == 0
        assert run_env(["add-employee", "alice", "--gross", "999999",
                        "--mandatory", "0"]).returncode == 0
        ro = run_env(["add-order", "alice", "--kind", "child_support",
                      "--priority", "1", "--cap", "100000"])
        assert ro.returncode == 0, ro.stderr
        oid = int(ro.stdout.strip())
        amt = ref_grossup(100000)
        assert run_env(["remit", "alice"]).returncode == 0
        rows = [ln.split() for ln in run_env(["audit"]).stdout.strip().splitlines()
                if ln.strip()]
        assert len(rows) == 1
        msg = f"1|1|{oid}|child_support|{amt}|{GENESIS}".encode()
        expect = hmac.new(custom.encode(), msg, hashlib.sha256).hexdigest()
        default = hmac.new(SECRET.encode(), msg, hashlib.sha256).hexdigest()
        assert rows[0][5] == expect
        assert rows[0][5] != default
        # the chain still verifies under the same custom key
        assert run_env(["audit-verify"]).stdout.strip() == "valid"

    def _build_chain(self, specs):
        """specs: list of (emp_id, order_id, kind, amount)."""
        chain = []
        prev = GENESIS
        for i, (eid, oid, kind, amt) in enumerate(specs, start=1):
            h = entry_hash(i, eid, oid, kind, amt, prev)
            chain.append({
                "seq": i, "employee_id": eid, "order_id": oid, "kind": kind,
                "amount": amt, "prev_hash": prev, "entry_hash": h,
            })
            prev = h
        return chain

    def _verify(self, chain):
        b64 = base64.b64encode(json.dumps(chain).encode()).decode()
        r = run(["audit-verify", "--chain", b64])
        assert r.returncode == 0
        return r.stdout.strip()

    def test_external_valid(self, fresh_db):
        init_db()
        chain = self._build_chain([(1, 1, "child_support", 142592), (1, 2, "creditor", 219231)])
        assert self._verify(chain) == "valid"

    def test_external_seq_gap(self, fresh_db):
        init_db()
        chain = self._build_chain([(1, 1, "child_support", 142592), (1, 2, "creditor", 219231)])
        chain[1]["seq"] = 3
        assert self._verify(chain) == "broken_at 2 seq_gap"

    def test_external_prev_hash_mismatch(self, fresh_db):
        init_db()
        chain = self._build_chain([(1, 1, "child_support", 142592), (1, 2, "creditor", 219231)])
        chain[1]["prev_hash"] = GENESIS
        assert self._verify(chain) == "broken_at 2 prev_hash_mismatch"

    def test_external_entry_hash_mismatch(self, fresh_db):
        init_db()
        chain = self._build_chain([(1, 1, "child_support", 142592)])
        chain[0]["amount"] = 99999
        assert self._verify(chain) == "broken_at 1 entry_hash_mismatch"

    def test_seq_gap_precedence(self, fresh_db):
        init_db()
        chain = self._build_chain([(1, 1, "child_support", 142592), (1, 2, "creditor", 219231)])
        chain[1]["seq"] = 9
        chain[1]["entry_hash"] = "deadbeef"
        assert self._verify(chain) == "broken_at 2 seq_gap"
