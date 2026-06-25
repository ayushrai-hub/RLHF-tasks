import requests

BASE_URL = "http://127.0.0.1:8080"

class TestMilestone2:
    def test_create_sliding_breaker(self):
        """Verify registration of sliding window log breakers and rejection of simple parameters."""
        r = requests.post(f"{BASE_URL}/api/breakers", json={
            "id": "sliding_1",
            "policy": "sliding",
            "failure_threshold": 3,
            "window_us": 100000
        })
        assert r.status_code == 201
        assert r.json()["window_us"] == 100000
        assert r.json()["recovery_timeout_us"] is None

        # Rejects if both window and recovery are passed
        r_invalid = requests.post(f"{BASE_URL}/api/breakers", json={
            "id": "sliding_2",
            "policy": "sliding",
            "failure_threshold": 3,
            "window_us": 100000,
            "recovery_timeout_us": 50000
        })
        assert r_invalid.status_code == 400

    def test_sliding_window_transition(self):
        """Verify sliding window transitions to OPEN when failures within the window hit the threshold."""
        # Threshold is 3, window is 100000

        # Report failure 1
        requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "sliding_1", "success": False})
        
        # Advance time by 40000, report failure 2 (total 2 in window)
        requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 40000})
        requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "sliding_1", "success": False})
        
        # Advance time by 70000 (total 110000 from start. failure 1 is now outside window).
        # Report failure 3 (total 2 in window: failure 2 and failure 3). Should stay CLOSED.
        requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 70000})
        r_f3 = requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "sliding_1", "success": False})
        assert r_f3.json()["state"] == "CLOSED"

        # Report failure 4 (total 3 in window: failure 2, 3, and 4). Should transition to OPEN.
        r_f4 = requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "sliding_1", "success": False})
        assert r_f4.json()["state"] == "OPEN"

    def test_sliding_window_auto_recovery(self):
        """Verify sliding window auto-recovery triggers after window_us timeout."""
        # Slide time beyond window_us (100000) from last state change
        requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 110000})
        
        r = requests.post(f"{BASE_URL}/api/check", json={"breaker_id": "sliding_1"})
        assert r.status_code == 200
        assert r.json()["allowed"] is True
        assert r.json()["state"] == "HALF-OPEN"

    def test_composite_check_success(self):
        """Verify composite check allows traffic when all breakers are CLOSED or HALF-OPEN."""
        # Create another simple breaker
        requests.post(f"{BASE_URL}/api/breakers", json={
            "id": "simple_comp_1",
            "policy": "simple",
            "failure_threshold": 2,
            "recovery_timeout_us": 50000
        })
        
        r = requests.post(f"{BASE_URL}/api/check", json={
            "breaker_ids": ["sliding_1", "simple_comp_1"]
        })
        assert r.status_code == 200
        assert r.json()["allowed"] is True
        assert "sliding_1" in r.json()["state_map"]
        assert "simple_comp_1" in r.json()["state_map"]

    def test_composite_check_denied(self):
        """Verify composite check blocks traffic when any queried breaker is OPEN."""
        # Trip simple_comp_1
        requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "simple_comp_1", "success": False})
        requests.post(f"{BASE_URL}/api/breakers/report", json={"id": "simple_comp_1", "success": False})
        
        r = requests.post(f"{BASE_URL}/api/check", json={
            "breaker_ids": ["sliding_1", "simple_comp_1"]
        })
        assert r.status_code == 200
        assert r.json()["allowed"] is False
        assert r.json()["denied_by"] == "simple_comp_1"

    def test_audit_logs_generation(self):
        """Verify audit log tracks composite checks with breaker array details."""
        r = requests.get(f"{BASE_URL}/api/audit")
        assert r.status_code == 200
        rows = r.json()["audit"]
        assert len(rows) > 0
        latest = rows[-1]
        assert "breaker_ids" in latest
        assert "allowed" in latest
        assert latest["denied_by"] == "simple_comp_1"

    def test_audit_breaker_id_filter(self):
        """Verify audit log filters matching records containing breaker_id."""
        r = requests.get(f"{BASE_URL}/api/audit?breaker_id=simple_comp_1")
        assert r.status_code == 200
        for row in r.json()["audit"]:
            assert "simple_comp_1" in row["breaker_ids"]

    def test_audit_since_id_filter(self):
        """Verify audit log filters matching records strictly greater than since_id."""
        r_all = requests.get(f"{BASE_URL}/api/audit")
        rows = r_all.json()["audit"]
        if len(rows) > 1:
            mid = rows[len(rows)//2]["id"]
            r_filtered = requests.get(f"{BASE_URL}/api/audit?since_id={mid}")
            for row in r_filtered.json()["audit"]:
                assert row["id"] > mid

    def test_audit_limit(self):
        """Verify audit log respects limit and is sorted ascending."""
        r = requests.get(f"{BASE_URL}/api/audit?limit=2")
        assert r.status_code == 200
        assert r.json()["count"] <= 2
        rows = r.json()["audit"]
        if len(rows) == 2:
            assert rows[0]["id"] < rows[1]["id"]

    def test_chartjs_script_tag(self):
        """Verify script tag containing chart.js is present in the dashboard HTML."""
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        assert "chart.js" in r.text
