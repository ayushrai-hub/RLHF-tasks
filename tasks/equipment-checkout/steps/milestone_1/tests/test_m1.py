"""Milestone 1 tests: init, add-equipment, add-borrower, list-equipment."""
import subprocess
import os
import pytest


def run(args):
    return subprocess.run(["/app/app"] + args, capture_output=True, text=True)


def run_ok(args):
    r = run(args)
    assert r.returncode == 0, f"Non-zero exit for {args}: {r.stdout} {r.stderr}"
    return r


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "test.db")
    run_ok(["init", path])
    return path


class TestMilestone1:
    def test_init_creates_db(self, tmp_path):
        path = str(tmp_path / "new.db")
        r = run(["init", path])
        assert r.returncode == 0
        assert os.path.exists(path)

    def test_init_idempotent(self, tmp_path):
        path = str(tmp_path / "new.db")
        run_ok(["init", path])
        r = run(["init", path])
        assert r.returncode == 0

    def test_init_prints_ok(self, tmp_path):
        path = str(tmp_path / "new.db")
        r = run(["init", path])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_tool(self, db):
        r = run(["add-equipment", db, "E001", "Power Drill", "tool", "500"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_electronics(self, db):
        r = run(["add-equipment", db, "E002", "Laptop", "electronics", "1500"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_furniture(self, db):
        r = run(["add-equipment", db, "E003", "Folding Table", "furniture", "200"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_invalid_category(self, db):
        r = run(["add-equipment", db, "E004", "Widget", "gadget", "100"])
        assert r.returncode == 1

    def test_add_equipment_duplicate(self, db):
        run_ok(["add-equipment", db, "E001", "Drill", "tool", "500"])
        r = run(["add-equipment", db, "E001", "Drill2", "tool", "600"])
        assert r.returncode == 1
        assert "equipment already exists: E001" in r.stdout

    def test_add_borrower_ok(self, db):
        r = run(["add-borrower", db, "B001", "Alice Thompson"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_borrower_duplicate(self, db):
        run_ok(["add-borrower", db, "B001", "Alice Thompson"])
        r = run(["add-borrower", db, "B001", "Alice Thompson"])
        assert r.returncode == 1
        assert "borrower already exists: B001" in r.stdout

    def test_list_equipment_empty(self, db):
        r = run_ok(["list-equipment", db])
        assert r.stdout.strip() == ""

    def test_list_equipment_columns(self, db):
        run_ok(["add-equipment", db, "E001", "Power Drill", "tool", "500"])
        r = run_ok(["list-equipment", db])
        cols = r.stdout.strip().split("\t")
        assert cols[0] == "E001"
        assert cols[1] == "Power Drill"
        assert cols[2] == "tool"
        assert cols[3] == "500"
        assert cols[4] == "available"

    def test_list_equipment_sorted_by_id(self, db):
        run_ok(["add-equipment", db, "Z001", "Zig", "tool", "100"])
        run_ok(["add-equipment", db, "A001", "Alpha", "electronics", "200"])
        run_ok(["add-equipment", db, "M001", "Mid", "furniture", "150"])
        r = run_ok(["list-equipment", db])
        ids = [line.split("\t")[0] for line in r.stdout.strip().splitlines()]
        assert ids == sorted(ids)

    def test_list_equipment_multiple(self, db):
        for i in range(1, 4):
            run_ok(["add-equipment", db, f"E{i:03d}", f"Item {i}", "tool", str(i * 100)])
        r = run_ok(["list-equipment", db])
        assert len(r.stdout.strip().splitlines()) == 3

    def test_add_multiple_borrowers(self, db):
        for i in range(1, 4):
            r = run(["add-borrower", db, f"B{i}", f"Borrower {i}"])
            assert r.returncode == 0

    # --- TRAP B: condition field tests ---

    def test_add_equipment_with_damaged_condition(self, db):
        """add-equipment accepts DAMAGED as a valid condition."""
        r = run(["add-equipment", db, "E010", "Broken Saw", "tool", "300", "DAMAGED"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_with_maintenance_condition(self, db):
        """add-equipment accepts MAINTENANCE as a valid condition."""
        r = run(["add-equipment", db, "E011", "Service Lift", "tool", "200", "MAINTENANCE"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_with_ok_condition_explicit(self, db):
        """add-equipment accepts explicit OK condition."""
        r = run(["add-equipment", db, "E012", "Normal Drill", "tool", "100", "OK"])
        assert r.returncode == 0
        assert "OK" in r.stdout

    def test_add_equipment_invalid_condition(self, db):
        """add-equipment rejects unknown condition values."""
        r = run(["add-equipment", db, "E013", "Widget", "tool", "100", "BROKEN"])
        assert r.returncode == 1

    def test_add_equipment_default_condition_ok(self, db):
        """Equipment with no condition arg defaults to OK in list-equipment."""
        run_ok(["add-equipment", db, "E001", "Drill", "tool", "100"])
        r = run_ok(["list-equipment", db])
        cols = r.stdout.strip().split("\t")
        assert len(cols) == 6, f"Expected 6 tab-separated columns, got {len(cols)}: {cols}"
        assert cols[5] == "OK"

    def test_list_equipment_shows_damaged_condition(self, db):
        """list-equipment outputs condition as the 6th column."""
        run_ok(["add-equipment", db, "E001", "Broken Drill", "tool", "100", "DAMAGED"])
        r = run_ok(["list-equipment", db])
        cols = r.stdout.strip().split("\t")
        assert len(cols) == 6, f"Expected 6 columns: {cols}"
        assert cols[5] == "DAMAGED"

    def test_list_equipment_shows_maintenance_condition(self, db):
        """list-equipment outputs MAINTENANCE condition in column 6."""
        run_ok(["add-equipment", db, "E001", "Scaffolding", "tool", "150", "MAINTENANCE"])
        r = run_ok(["list-equipment", db])
        cols = r.stdout.strip().split("\t")
        assert len(cols) == 6, f"Expected 6 columns: {cols}"
        assert cols[5] == "MAINTENANCE"

    def test_list_equipment_condition_per_row(self, db):
        """Multiple rows each show their own condition."""
        run_ok(["add-equipment", db, "E001", "Drill", "tool", "100", "OK"])
        run_ok(["add-equipment", db, "E002", "Broken Wrench", "tool", "50", "DAMAGED"])
        run_ok(["add-equipment", db, "E003", "Lift", "tool", "200", "MAINTENANCE"])
        r = run_ok(["list-equipment", db])
        rows = {ln.split("\t")[0]: ln.split("\t") for ln in r.stdout.strip().splitlines()}
        assert rows["E001"][5] == "OK"
        assert rows["E002"][5] == "DAMAGED"
        assert rows["E003"][5] == "MAINTENANCE"
