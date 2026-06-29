"""Milestone 3 tests: chain-verify, rental-report."""
import subprocess
import sqlite3
import math
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


class TestMilestone3:
    def test_chain_verify_empty(self, db):
        r = run_ok(["chain-verify", db])
        assert r.returncode == 0
        assert "TAMPERED" not in r.stdout

    def test_chain_verify_valid_single(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        r = run_ok(["chain-verify", db])
        assert r.returncode == 0
        assert "TAMPERED" not in r.stdout

    def test_chain_verify_valid_multiple(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-10"])
        run_ok(["checkin", db, "2", "2024-01-12"])
        r = run_ok(["chain-verify", db])
        assert r.returncode == 0
        assert "TAMPERED" not in r.stdout

    def test_chain_verify_tampered_hash(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        conn = sqlite3.connect(db)
        conn.execute("UPDATE audit_chain SET hash='deadbeef' WHERE chain_id=1 AND equipment_id='E001'")
        conn.commit()
        conn.close()
        r = run(["chain-verify", db])
        assert r.returncode == 1
        assert "TAMPERED E001 1" in r.stdout

    def test_chain_verify_tampered_daily_rate(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        conn = sqlite3.connect(db)
        conn.execute("UPDATE audit_chain SET daily_rate_cents=9999 WHERE equipment_id='E001'")
        conn.commit()
        conn.close()
        r = run(["chain-verify", db])
        assert r.returncode == 1
        assert "TAMPERED" in r.stdout
        assert "E001" in r.stdout

    def test_chain_verify_scans_all_equipment(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-10"])
        conn = sqlite3.connect(db)
        conn.execute("UPDATE audit_chain SET hash='badhash' WHERE equipment_id='E002'")
        conn.commit()
        conn.close()
        r = run(["chain-verify", db])
        assert r.returncode == 1
        assert "TAMPERED E002 1" in r.stdout
        assert "TAMPERED E001" not in r.stdout

    def test_chain_verify_sequential_chain_e001(self, db):
        """Two checkouts on same equipment — chain is sequential."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-01"])
        run_ok(["checkin", db, "1", "2024-01-05"])
        run_ok(["checkout", db, "E001", "B002", "2024-02-01"])
        r = run_ok(["chain-verify", db])
        assert r.returncode == 0
        assert "TAMPERED" not in r.stdout

    def test_chain_verify_tampers_second_entry(self, db):
        run_ok(["checkout", db, "E001", "B001", "2024-01-01"])
        run_ok(["checkin", db, "1", "2024-01-05"])
        run_ok(["checkout", db, "E001", "B002", "2024-02-01"])
        conn = sqlite3.connect(db)
        conn.execute("UPDATE audit_chain SET hash='deadbeef' WHERE chain_id=2 AND equipment_id='E001'")
        conn.commit()
        conn.close()
        r = run(["chain-verify", db])
        assert r.returncode == 1
        assert "TAMPERED E001 2" in r.stdout

    # --- TRAP C: chain-verify must use rate from audit_chain, not current equipment table ---

    def test_chain_verify_uses_stored_rate_not_current(self, db):
        """After updating equipment rate directly, chain-verify must still pass.
        chain-verify reads daily_rate_cents from audit_chain (stored at checkout time),
        NOT from the equipment table. If it re-reads from equipment, it will falsely TAMPER."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        # Simulate a post-checkout rate change directly in the equipment table
        conn = sqlite3.connect(db)
        conn.execute("UPDATE equipment SET daily_rate_cents=9999 WHERE equipment_id='E001'")
        conn.commit()
        conn.close()
        # chain-verify must still pass because audit_chain stores the original rate (100)
        r = run(["chain-verify", db])
        assert r.returncode == 0, (
            "chain-verify must use daily_rate_cents from audit_chain row, not current equipment table"
        )
        assert "TAMPERED" not in r.stdout

    def test_chain_verify_uses_stored_rate_two_checkouts(self, db):
        """Rate change between two checkouts: each chain entry uses its own stored rate."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-01"])
        run_ok(["checkin", db, "1", "2024-01-05"])
        # Change rate in equipment table between checkouts
        conn = sqlite3.connect(db)
        conn.execute("UPDATE equipment SET daily_rate_cents=250 WHERE equipment_id='E001'")
        conn.commit()
        conn.close()
        run_ok(["checkout", db, "E001", "B002", "2024-02-01"])
        # Both entries are valid: chain entry 1 used rate=100, chain entry 2 used rate=250
        r = run(["chain-verify", db])
        assert r.returncode == 0
        assert "TAMPERED" not in r.stdout

    # --- Rental report tests ---

    def test_rental_report_empty(self, db):
        r = run_ok(["rental-report", db])
        assert "total_rentals=0" in r.stdout
        assert "p50_fee_cents=0.00" in r.stdout
        assert "p90_fee_cents=0.00" in r.stdout
        assert "p95_fee_cents=0.00" in r.stdout
        assert "std_fee_cents=0.00" in r.stdout
        assert "p90_duration_minutes=0.00" in r.stdout

    def test_rental_report_format(self, db):
        """rental-report must output exactly 6 lines in the specified order."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        r = run_ok(["rental-report", db])
        lines = r.stdout.strip().splitlines()
        assert len(lines) == 6, f"Expected 6 output lines, got {len(lines)}: {lines}"
        assert lines[0].startswith("total_rentals=")
        assert lines[1].startswith("p50_fee_cents=")
        assert lines[2].startswith("p90_fee_cents=")
        assert lines[3].startswith("p95_fee_cents=")
        assert lines[4].startswith("std_fee_cents=")
        assert lines[5].startswith("p90_duration_minutes=")

    def test_rental_report_values(self, db):
        """E001: 5 days * 100 = 500. E002: 2 days * 300 = 600.
        Fees sorted: [500, 600].
        p50: rank=ceil(0.5*2)=1 -> 500.00
        p90: rank=ceil(0.9*2)=ceil(1.8)=2 -> 600.00
        p95: rank=ceil(0.95*2)=2 -> 600.00
        mean=550, variance=((500-550)^2+(600-550)^2)/2=2500, std=50.00
        Durations sorted: [2, 5] days -> [2880, 7200] min. p90: ceil(0.9*2)=2 -> 7200 min."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-10"])
        run_ok(["checkin", db, "2", "2024-01-12"])
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert lines["total_rentals"] == "2"
        assert abs(float(lines["p50_fee_cents"]) - 500.0) < 0.01
        assert abs(float(lines["p90_fee_cents"]) - 600.0) < 0.01
        assert abs(float(lines["p95_fee_cents"]) - 600.0) < 0.01
        assert abs(float(lines["std_fee_cents"]) - 50.0) < 0.01
        # p90 duration: durations [2 days, 5 days] sorted -> [2880, 7200]; ceil(0.9*2)=2 -> sorted[1]=7200
        assert abs(float(lines["p90_duration_minutes"]) - 7200.0) < 0.01

    def test_rental_report_population_stddev(self, db):
        """Population stddev with fees [100, 300, 100]: mean=500/3, std=sqrt(240000/27)~94.28."""
        run_ok(["add-equipment", db, "E003", "Chair", "furniture", "100"])
        run_ok(["checkout", db, "E001", "B001", "2024-01-01"])
        run_ok(["checkin", db, "1", "2024-01-02"])
        run_ok(["checkout", db, "E002", "B001", "2024-01-01"])
        run_ok(["checkin", db, "2", "2024-01-02"])
        run_ok(["checkout", db, "E003", "B001", "2024-01-01"])
        run_ok(["checkin", db, "3", "2024-01-02"])
        r = run_ok(["rental-report", db])
        # fees=[100, 300, 100]; population stddev=sqrt(8888.89)~94.28
        std_line = [ln for ln in r.stdout.strip().splitlines() if ln.startswith("std_fee_cents=")][0]
        std_val = std_line.split("=")[1]
        assert "." in std_val and len(std_val.split(".")[1]) == 2
        expected_std = math.sqrt(((-200/3)**2 + (400/3)**2 + (-200/3)**2) / 3)
        assert abs(float(std_val) - expected_std) < 0.1, f"Expected ~{expected_std:.2f}, got {std_val}"

    def test_rental_report_only_closed(self, db):
        """Open checkouts are excluded from rental-report."""
        run_ok(["checkout", db, "E001", "B001", "2024-01-10"])
        run_ok(["checkin", db, "1", "2024-01-15"])
        run_ok(["checkout", db, "E002", "B002", "2024-01-20"])
        # E002 is still open
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert lines["total_rentals"] == "1"

    def test_rental_report_p50_nearest_rank(self, db):
        """5 fees: [100,200,300,400,500]. p50: rank=ceil(0.5*5)=3 -> 300."""
        run_ok(["add-equipment", db, "E003", "C", "tool", "200"])
        run_ok(["add-equipment", db, "E004", "D", "tool", "400"])
        run_ok(["add-equipment", db, "E005", "E", "tool", "500"])
        run_ok(["checkout", db, "E001", "B001", "2024-01-01"])
        run_ok(["checkin", db, "1", "2024-01-02"])    # 1*100=100
        run_ok(["checkout", db, "E003", "B001", "2024-01-01"])
        run_ok(["checkin", db, "2", "2024-01-02"])    # 1*200=200
        run_ok(["checkout", db, "E002", "B001", "2024-01-01"])
        run_ok(["checkin", db, "3", "2024-01-02"])    # 1*300=300
        run_ok(["checkout", db, "E004", "B001", "2024-01-01"])
        run_ok(["checkin", db, "4", "2024-01-02"])    # 1*400=400
        run_ok(["checkout", db, "E005", "B001", "2024-01-01"])
        run_ok(["checkin", db, "5", "2024-01-02"])    # 1*500=500
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert abs(float(lines["p50_fee_cents"]) - 300.0) < 0.01
        assert abs(float(lines["p95_fee_cents"]) - 500.0) < 0.01

    # --- TRAP A: p90 nearest-rank boundary (floor vs ceil gives different element) ---

    def test_rental_report_p90_nearest_rank_boundary(self, db):
        """7 fees [100..700]: p90=ceil(0.9*7)=ceil(6.3)=7 -> sorted[6]=700.
        floor(6.3)=6 -> sorted[5]=600 is WRONG.
        p50=ceil(0.5*7)=ceil(3.5)=4 -> sorted[3]=400 (floor gives 300)."""
        for idx, rate in enumerate([100, 200, 300, 400, 500, 600, 700], start=3):
            run_ok(["add-equipment", db, f"E{idx:03d}", f"Item{idx}", "tool", str(rate)])
        cid = 1
        for eid in ["E003", "E004", "E005", "E006", "E007", "E008", "E009"]:
            run_ok(["checkout", db, eid, "B001", "2024-06-01"])
            run_ok(["checkin", db, str(cid), "2024-06-02"])
            cid += 1
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert lines["total_rentals"] == "7"
        assert abs(float(lines["p90_fee_cents"]) - 700.0) < 0.01, (
            f"p90 wrong: ceil(0.9*7)=7 -> 700, got {lines['p90_fee_cents']}"
        )
        assert abs(float(lines["p50_fee_cents"]) - 400.0) < 0.01, (
            f"p50 wrong: ceil(0.5*7)=4 -> 400, got {lines['p50_fee_cents']}"
        )

    # --- TRAP A: population stddev discriminator (5 values, pop vs sample differ by ~33) ---

    def test_rental_report_pop_stddev_five_values(self, db):
        """5 fees [200,400,600,800,1000]: pop_std=sqrt(80000)~282.84; sample_std~316.23.
        Tests that implementation divides by N not N-1."""
        for idx, rate in enumerate([200, 400, 600, 800, 1000], start=3):
            run_ok(["add-equipment", db, f"E{idx:03d}", f"Item{idx}", "tool", str(rate)])
        for i, eid in enumerate(["E003", "E004", "E005", "E006", "E007"], start=1):
            run_ok(["checkout", db, eid, "B001", "2024-07-01"])
            run_ok(["checkin", db, str(i), "2024-07-02"])
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        expected_pop_std = math.sqrt(80000)   # ~282.843
        expected_sample_std = math.sqrt(100000)  # ~316.228
        actual = float(lines["std_fee_cents"])
        assert abs(actual - expected_pop_std) < 0.05, (
            f"Expected pop stddev ~{expected_pop_std:.2f} (÷N), got {actual:.2f}. "
            f"If you got ~{expected_sample_std:.2f} you divided by N-1 (sample stddev) — use N."
        )

    # --- TRAP A: sharper population stddev discriminator (4 values, pop vs sample differ at 2dp) ---

    def test_rental_report_pop_stddev_four_values(self, db):
        """4 fees [100,200,300,400]: pop_std=sqrt(12500)~111.80; sample_std=sqrt(16667)~129.10.
        Values differ at 2 decimal places — dividing by N-1 gives wrong result."""
        run_ok(["add-equipment", db, "E003", "C", "tool", "200"])
        run_ok(["add-equipment", db, "E004", "D", "tool", "400"])
        run_ok(["checkout", db, "E001", "B001", "2024-08-01"])
        run_ok(["checkin", db, "1", "2024-08-02"])   # 1*100=100
        run_ok(["checkout", db, "E003", "B001", "2024-08-01"])
        run_ok(["checkin", db, "2", "2024-08-02"])   # 1*200=200
        run_ok(["checkout", db, "E002", "B001", "2024-08-01"])
        run_ok(["checkin", db, "3", "2024-08-02"])   # 1*300=300
        run_ok(["checkout", db, "E004", "B001", "2024-08-01"])
        run_ok(["checkin", db, "4", "2024-08-02"])   # 1*400=400
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        expected_pop_std = math.sqrt(12500)          # ~111.803
        expected_sample_std = math.sqrt(50000 / 3)  # ~129.099
        actual = float(lines["std_fee_cents"])
        assert abs(actual - expected_pop_std) < 0.05, (
            f"Expected pop stddev ~{expected_pop_std:.2f} (divide by N=4), got {actual:.2f}. "
            f"If you got ~{expected_sample_std:.2f} you divided by N-1=3 (sample stddev) — use population stddev."
        )

    # --- TRAP B: p90_duration_minutes nearest-rank boundary with N=11 ---

    def test_rental_report_p90_duration_ceil_boundary(self, db):
        """N=11 rentals with durations [1..11] days.
        p90_duration: ceil(0.9*11)=ceil(9.9)=10 -> sorted[9]=10 days=14400 min.
        floor(9.9)=9 -> sorted[8]=9 days=12960 min (WRONG)."""
        # Add E003..E011 on top of fixture E001, E002 (9 more items)
        for i in range(3, 12):
            run_ok(["add-equipment", db, f"E{i:03d}", f"Item{i}", "tool", "100"])
        eids = [f"E{i:03d}" for i in range(1, 12)]  # E001..E011
        base = "2024-09-01"
        for idx, eid in enumerate(eids, start=1):
            # duration = idx days: checkout on Sep 1, checkin on Sep (1+idx)
            checkin = f"2024-09-{1 + idx:02d}"
            run_ok(["checkout", db, eid, "B001", base])
            run_ok(["checkin", db, str(idx), checkin])
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert lines["total_rentals"] == "11"
        # p90 duration: ceil(0.9*11)=10 -> sorted[9]=10 days=14400 min
        assert abs(float(lines["p90_duration_minutes"]) - 14400.0) < 0.01, (
            f"p90_duration_minutes wrong: ceil(0.9*11)=10 -> sorted[9]=10 days=14400 min, "
            f"got {lines['p90_duration_minutes']}. "
            f"If you got 12960.00 (9 days), you used floor(9.9)=9 instead of ceil(9.9)=10."
        )

    def test_rental_report_p90_duration_single(self, db):
        """Single rental: duration=3 days=4320 min. p90 with n=1: ceil(0.9*1)=1 -> sorted[0]=4320."""
        run_ok(["checkout", db, "E001", "B001", "2024-10-01"])
        run_ok(["checkin", db, "1", "2024-10-04"])   # 3 days
        r = run_ok(["rental-report", db])
        lines = {ln.split("=")[0]: ln.split("=")[1] for ln in r.stdout.strip().splitlines()}
        assert abs(float(lines["p90_duration_minutes"]) - 4320.0) < 0.01
