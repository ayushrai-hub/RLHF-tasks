"""Milestone 2 tests: checkout, checkin, checkout-stats."""
import sqlite3
import subprocess
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
    run_ok(["add-equipment", path, "E001", "Drill", "tool", "100"])
    run_ok(["add-equipment", path, "E002", "Laptop", "electronics", "300"])
    run_ok(["add-borrower", path, "B001", "Alice"])
    run_ok(["add-borrower", path, "B002", "Bob"])
    return path


class TestMilestone2:
    def test_checkout_ok(self, db):
        r = run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        assert "OK checkout_id=" in r.stdout

    def test_checkout_sequential_ids(self, db):
        r1 = run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-12"])
        r2 = run_ok(["checkout", db, "E001", "B002", "2024-01-15"])
        id1 = int(r1.stdout.strip().split("=")[1])
        id2 = int(r2.stdout.strip().split("=")[1])
        assert id2 == id1 + 1

    def test_checkout_equipment_not_found(self, db):
        r = run(["checkout", db, "E999", "B001", "2024-01-10"])
        assert r.returncode == 1
        assert "equipment not found: E999" in r.stdout

    def test_checkout_borrower_not_found(self, db):
        r = run(["checkout", db, "E001", "B999", "2024-01-10"])
        assert r.returncode == 1
        assert "borrower not found: B999" in r.stdout

    def test_checkout_already_checked_out(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run(["checkout", db, "E001", "B002", "2024-01-11"])
        assert r.returncode == 1
        assert "equipment not available: E001" in r.stdout

    def test_checkin_ok(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run_ok(["checkin", db, "1", "2024-01-15"])
        # 5 days * 100 cents/day = 500
        assert r.stdout.strip() == "OK fee_cents=500"

    def test_checkin_fee_calculation(self, db):
        run_ok(["checkout", db, "E002", "B001", "2024-03-01"])
        r = run_ok(["checkin", db, "1", "2024-03-04"])
        # 3 days * 300 cents/day = 900
        assert r.stdout.strip() == "OK fee_cents=900"

    def test_checkin_checkout_not_found(self, db):
        r = run(["checkin", db, "999", "2024-01-15"])
        assert r.returncode == 1
        assert "checkout not found: 999" in r.stdout

    def test_checkin_already_closed(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        r = run(["checkin", db, "1", "2024-01-20"])
        assert r.returncode == 1
        assert "checkout already closed: 1" in r.stdout

    def test_equipment_available_after_checkin(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        # Should be able to check out again
        r = run_ok(["checkout", db, "E001", "B002", "2024-01-20"])
        assert "OK checkout_id=" in r.stdout

    def test_equipment_checked_out_status_in_list(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run_ok(["list-equipment", db])
        e001_line = [ln for ln in r.stdout.strip().splitlines() if ln.startswith("E001")][0]
        assert e001_line.split("\t")[4] == "checked_out"

    def test_equipment_available_status_after_checkin(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        r = run_ok(["list-equipment", db])
        e001_line = [ln for ln in r.stdout.strip().splitlines() if ln.startswith("E001")][0]
        assert e001_line.split("\t")[4] == "available"

    def test_checkout_stats_empty(self, db):
        r = run_ok(["checkout-stats", db])
        assert "total_checkouts=0" in r.stdout
        assert "total_returned=0" in r.stdout
        assert "avg_fee_cents=0.00" in r.stdout

    def test_checkout_stats_open_only(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run_ok(["checkout-stats", db])
        assert "total_checkouts=1" in r.stdout
        assert "total_returned=0" in r.stdout
        assert "avg_fee_cents=0.00" in r.stdout

    def test_checkout_stats_one_completed(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        r = run_ok(["checkout-stats", db])
        assert "total_checkouts=1" in r.stdout
        assert "total_returned=1" in r.stdout
        assert "avg_fee_cents=500.00" in r.stdout

    def test_checkout_stats_two_decimal_places(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        r = run_ok(["checkout-stats", db])
        avg_line = [ln for ln in r.stdout.strip().splitlines() if ln.startswith("avg_fee_cents=")][0]
        val = avg_line.split("=")[1]
        assert "." in val
        assert len(val.split(".")[1]) == 2

    def test_checkout_stats_multiple_completed(self, db):
        # E001: 5 days * 100 = 500; E002: 3 days * 300 = 900; avg = (500+900)/2 = 700
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-10"])
        run_ok(["checkin", db, "2", "2024-01-13"])
        r = run_ok(["checkout-stats", db])
        assert "total_checkouts=2" in r.stdout
        assert "total_returned=2" in r.stdout
        assert "avg_fee_cents=700.00" in r.stdout

    def test_checkin_sets_checkin_date_in_db(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT checkin_date, fee_cents, status FROM checkouts WHERE checkout_id=1"
        ).fetchone()
        conn.close()
        checkin_date, fee_cents, status = row
        assert checkin_date == "2024-01-15"
        assert fee_cents == 500
        assert status == "closed"

    def test_checkin_sets_returned_at_in_db(self, db):
        """checkin must persist the return date (checkin_date) in the DB as non-NULL."""
        run_ok(["checkout", db, "E002", "B002", "2024-03-01"])
        run_ok(["checkin", db, "1", "2024-03-04"])
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT checkin_date FROM checkouts WHERE checkout_id=1"
        ).fetchone()
        conn.close()
        assert row is not None
        returned_at = row[0]
        assert returned_at is not None, "returned_at (checkin_date) must be set in DB after checkin"
        assert returned_at == "2024-03-04"

    def test_checkout_stats_total_fee_cents_with_loans(self, db):
        """checkout-stats must report total_fee_cents summing all closed-checkout fees."""
        # E001: 5 days * 100 cents/day = 500; E002: 3 days * 300 cents/day = 900; total = 1400
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-10"])
        run_ok(["checkin", db, "2", "2024-01-13"])
        r = run_ok(["checkout-stats", db])
        assert "total_fee_cents=1400" in r.stdout

    # --- TRAP B: DAMAGED equipment blocks checkout ---

    def test_checkout_damaged_equipment_blocked(self, db):
        """DAMAGED equipment must be rejected at checkout (availability gate)."""
        run_ok(["add-equipment", db, "E010", "Broken Saw", "tool", "200", "DAMAGED"])
        r = run(["checkout", db, "E010", "B001", "2024-01-10"])
        assert r.returncode == 1
        assert "equipment not available: E010" in r.stdout

    def test_checkout_damaged_error_before_borrower_check(self, db):
        """DAMAGED check happens before borrower existence check."""
        run_ok(["add-equipment", db, "E010", "Busted Crane", "tool", "500", "DAMAGED"])
        # B999 does not exist, but DAMAGED check fires first -> "not available" not "borrower not found"
        r = run(["checkout", db, "E010", "B999", "2024-01-10"])
        assert r.returncode == 1
        assert "equipment not available: E010" in r.stdout
        assert "borrower not found" not in r.stdout

    # --- TRAP B: MAINTENANCE fee multiplier with banker's rounding ---

    def test_checkin_maintenance_simple_surcharge(self, db):
        """MAINTENANCE: 3 days x 200 = 600, x1.5 = 900 (exact, no rounding)."""
        run_ok(["add-equipment", db, "E010", "Heavy Loader", "tool", "200", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-01-10"])
        r = run_ok(["checkin", db, "1", "2024-01-13"])
        assert "fee_cents=900" in r.stdout

    def test_checkin_maintenance_bankers_round_down(self, db):
        """MAINTENANCE banker rounding: 3 days x 101 = 303, x1.5 = 454.5 -> 454 (even, rounds down)."""
        run_ok(["add-equipment", db, "E010", "Scaffolding", "tool", "101", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-02-01"])
        # First checkout in this test's db -> checkout_id=1
        r = run_ok(["checkin", db, "1", "2024-02-04"])
        assert "fee_cents=454" in r.stdout, (
            f"Expected fee_cents=454 (banker_round(454.5)=454), got: {r.stdout.strip()}"
        )

    def test_checkin_maintenance_bankers_round_up(self, db):
        """MAINTENANCE banker rounding: 3 days x 103 = 309, x1.5 = 463.5 -> 464 (odd floor, rounds up)."""
        run_ok(["add-equipment", db, "E010", "Crane Arm", "tool", "103", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-03-01"])
        r = run_ok(["checkin", db, "1", "2024-03-04"])
        assert "fee_cents=464" in r.stdout, (
            f"Expected fee_cents=464 (banker_round(463.5)=464), got: {r.stdout.strip()}"
        )

    def test_checkin_ok_condition_unaffected(self, db):
        """OK condition: standard fee with no multiplier."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run_ok(["checkin", db, "1", "2024-01-15"])
        # 5 days * 100 = 500 (no multiplier)
        assert r.stdout.strip() == "OK fee_cents=500"

    def test_checkin_maintenance_fee_stored_in_db(self, db):
        """MAINTENANCE surcharge must be persisted in checkouts.fee_cents."""
        run_ok(["add-equipment", db, "E010", "Lift", "tool", "200", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-13"])  # 3 * 200 * 1.5 = 900
        conn = sqlite3.connect(db)
        row = conn.execute("SELECT fee_cents FROM checkouts WHERE checkout_id=1").fetchone()
        conn.close()
        assert row[0] == 900, f"Expected fee_cents=900 stored in DB, got {row[0]}"

    def test_checkin_maintenance_bankers_round_154(self, db):
        """MAINTENANCE banker rounding: 1 day x 103 = 103, x1.5 = 154.5 -> 154 (even floor, round down).
        Standard rounding gives 155. Assert exactly 154, not 155."""
        run_ok(["add-equipment", db, "E010", "Precision Rig", "tool", "103", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-05-01"])
        r = run_ok(["checkin", db, "1", "2024-05-02"])
        assert "fee_cents=154" in r.stdout, (
            f"Expected fee_cents=154 (banker_round(154.5)=154, floor 154 is even), "
            f"not 155 (standard rounding). Got: {r.stdout.strip()}"
        )

    def test_checkin_maintenance_bankers_round_152(self, db):
        """MAINTENANCE banker rounding: 1 day x 101 = 101, x1.5 = 151.5 -> 152 (odd floor, round up).
        151 is odd so banker's rounds up to 152. Assert exactly 152."""
        run_ok(["add-equipment", db, "E010", "Heavy Rig", "tool", "101", "MAINTENANCE"])
        run_ok(["checkout", db, "E010", "B001", "2024-06-01"])
        r = run_ok(["checkin", db, "1", "2024-06-02"])
        assert "fee_cents=152" in r.stdout, (
            f"Expected fee_cents=152 (banker_round(151.5)=152, floor 151 is odd -> round up). "
            f"Got: {r.stdout.strip()}"
        )
