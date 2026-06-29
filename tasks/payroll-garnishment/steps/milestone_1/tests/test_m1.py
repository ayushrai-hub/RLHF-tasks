"""Milestone 1 tests: init, employees, orders, validation."""
import os
import shutil
import subprocess

import pytest

APP_DIR = "/app"
BINARY = "/app/pay"
DATA_DIR = "/app/data"


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
    backup = DATA_DIR + "_bak_m1"
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


def run(args):
    return subprocess.run([BINARY] + list(args), capture_output=True, text=True)


def init_db():
    r = run(["init"])
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "ok"


def add_employee(name, gross=200000, mandatory=40000):
    r = run(["add-employee", name, "--gross", str(gross), "--mandatory", str(mandatory)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


def add_order(emp, kind, priority, cap):
    r = run(["add-order", emp, "--kind", kind, "--priority", str(priority), "--cap", str(cap)])
    assert r.returncode == 0, r.stderr
    return int(r.stdout.strip())


class TestMilestone1:
    def test_init_prints_ok(self, fresh_db):
        init_db()

    def test_init_idempotent(self, fresh_db):
        init_db()
        init_db()

    def test_add_employee_returns_id(self, fresh_db):
        init_db()
        assert add_employee("alice") == 1

    def test_add_employee_duplicate_exists(self, fresh_db):
        init_db()
        add_employee("alice")
        r = run(["add-employee", "alice", "--gross", "100000", "--mandatory", "0"])
        assert r.returncode != 0
        assert r.stdout.strip() == "exists"

    def test_add_employee_fractional_gross_bad_input(self, fresh_db):
        init_db()
        r = run(["add-employee", "alice", "--gross", "100.5", "--mandatory", "0"])
        assert r.returncode != 0
        assert r.stdout.strip() == "bad_input"

    def test_add_employee_mandatory_exceeds_gross_bad_input(self, fresh_db):
        init_db()
        r = run(["add-employee", "alice", "--gross", "100000", "--mandatory", "100001"])
        assert r.returncode != 0
        assert r.stdout.strip() == "bad_input"

    def test_add_employee_nonpositive_gross_bad_input(self, fresh_db):
        init_db()
        for bad in ["0", "-5"]:
            r = run(["add-employee", "X" + bad, "--gross", bad, "--mandatory", "0"])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    def test_add_order_returns_id(self, fresh_db):
        init_db()
        add_employee("alice")
        assert add_order("alice", "child_support", 1, 60000) == 1

    def test_add_order_unknown_employee_not_found(self, fresh_db):
        init_db()
        r = run(["add-order", "ghost", "--kind", "creditor", "--priority", "1", "--cap", "100"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"

    def test_add_order_bad_priority_bad_input(self, fresh_db):
        init_db()
        add_employee("alice")
        for bad in ["0", "-1", "2.5"]:
            r = run(["add-order", "alice", "--kind", "creditor", "--priority", bad, "--cap", "100"])
            assert r.returncode != 0, bad
            assert r.stdout.strip() == "bad_input", bad

    def test_add_order_bad_cap_bad_input(self, fresh_db):
        init_db()
        add_employee("alice")
        r = run(["add-order", "alice", "--kind", "creditor", "--priority", "1", "--cap", "0"])
        assert r.returncode != 0
        assert r.stdout.strip() == "bad_input"

    def test_employees_sorted_by_name(self, fresh_db):
        init_db()
        add_employee("carol")
        add_employee("alice")
        add_employee("bob")
        r = run(["employees"])
        names = [ln.split()[1] for ln in r.stdout.strip().splitlines() if ln.strip()]
        assert names == ["alice", "bob", "carol"]

    def test_employees_full_row(self, fresh_db):
        init_db()
        add_employee("alice", gross=200000, mandatory=40000)
        r = run(["employees"])
        rows = [ln.split() for ln in r.stdout.strip().splitlines() if ln.strip()]
        assert rows[0] == ["1", "alice", "200000", "40000"]

    def test_orders_ordered_by_priority_then_id(self, fresh_db):
        init_db()
        add_employee("alice")
        add_order("alice", "creditor", 3, 50000)
        add_order("alice", "child_support", 1, 60000)
        add_order("alice", "student_loan", 1, 30000)  # same priority, later id
        r = run(["orders", "alice"])
        rows = [ln.split() for ln in r.stdout.strip().splitlines() if ln.strip()]
        # priority 1 entries first in id order, then priority 3.
        kinds = [x[1] for x in rows]
        assert kinds == ["child_support", "student_loan", "creditor"]

    def test_orders_unknown_employee_not_found(self, fresh_db):
        init_db()
        r = run(["orders", "ghost"])
        assert r.returncode != 0
        assert r.stdout.strip() == "not_found"
