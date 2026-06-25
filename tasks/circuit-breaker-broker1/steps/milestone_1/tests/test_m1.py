import requests

BASE_URL = "http://127.0.0.1:8080"

class TestMilestone1:
    def test_health(self):
        """Verify health endpoint is active and returns status ok."""
        r = requests.get(f"{BASE_URL}/api/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_now_clock(self):
        """Verify clock now_us initially returns 0."""
        r = requests.get(f"{BASE_URL}/api/now")
        assert r.status_code == 200
        assert r.json() == {"now_us": 0}

    def test_advance_clock(self):
        """Verify admin advance endpoint shifts time correctly and rejects invalid values."""
        # Valid advance
        r = requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 5000})
        assert r.status_code == 200
        assert r.json() == {"now_us": 5000}
        
        # Verify state persisted
        r = requests.get(f"{BASE_URL}/api/now")
        assert r.json() == {"now_us": 5000}
        
        # Invalid advance
        r = requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": -100})
        assert r.status_code == 400

    def test_breaker_registration(self):
        """Verify breaker registration stores values and enforces ID uniqueness."""
        breaker_id = "test_breaker_1"
        # Initial creation
        r = requests.post(f"{BASE_URL}/api/breakers", json={
            "id": breaker_id,
            "policy": "simple",
            "failure_threshold": 3,
            "recovery_timeout_us": 100000
        })
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == breaker_id
        assert data["policy"] == "simple"
        assert data["failure_threshold"] == 3
        assert data["recovery_timeout_us"] == 100000
        assert data["state"] == "CLOSED"
        assert data["failure_count"] == 0

        # Duplicate registration
        r = requests.post(f"{BASE_URL}/api/breakers", json={
            "id": breaker_id,
            "policy": "simple",
            "failure_threshold": 5,
            "recovery_timeout_us": 200000
        })
        assert r.status_code == 409

    def test_breaker_lookup(self):
        """Verify breaker lookup returns correct payload and 404 for unknown breaker."""
        r = requests.get(f"{BASE_URL}/api/breakers/test_breaker_1")
        assert r.status_code == 200
        assert r.json()["id"] == "test_breaker_1"

        r = requests.get(f"{BASE_URL}/api/breakers/unknown_breaker")
        assert r.status_code == 404

    def test_breaker_failure_reporting(self):
        """Verify breaker state transitions CLOSED -> OPEN after failure threshold reached."""
        breaker_id = "test_breaker_2"
        # Register first
        requests.post(f"{BASE_URL}/api/breakers", json={
            "id": breaker_id,
            "policy": "simple",
            "failure_threshold": 2,
            "recovery_timeout_us": 50000
        })
        
        # Report failure 1 (failure count 1)
        r = requests.post(f"{BASE_URL}/api/breakers/report", json={
            "id": breaker_id,
            "success": False
        })
        assert r.status_code == 200
        assert r.json()["state"] == "CLOSED"
        assert r.json()["failure_count"] == 1

        # Report failure 2 (failure count 2 -> transitions to OPEN)
        r = requests.post(f"{BASE_URL}/api/breakers/report", json={
            "id": breaker_id,
            "success": False
        })
        assert r.status_code == 200
        assert r.json()["state"] == "OPEN"

    def test_check_open_breaker(self):
        """Verify route check is denied with retry time when circuit is OPEN."""
        r = requests.post(f"{BASE_URL}/api/check", json={
            "breaker_id": "test_breaker_2"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["allowed"] is False
        assert data["state"] == "OPEN"
        assert data["retry_after_us"] > 0

    def test_check_half_open_auto_transition(self):
        """Verify that circuit automatically transitions to HALF-OPEN after timeout."""
        # Current time is 5000 (advanced in previous test). Wait, we need to advance clock.
        # Advance by 60000 -> now is 65000. Timeout was 50000, so it should transition.
        requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 60000})
        
        # Perform check (which triggers auto-transition)
        r = requests.post(f"{BASE_URL}/api/check", json={
            "breaker_id": "test_breaker_2"
        })
        assert r.status_code == 200
        assert r.json()["allowed"] is True
        assert r.json()["state"] == "HALF-OPEN"

    def test_half_open_recovery(self):
        """Verify half-open circuit transitions back to CLOSED on successful report."""
        breaker_id = "test_breaker_2"
        # Report success in HALF-OPEN state -> transitions to CLOSED
        r = requests.post(f"{BASE_URL}/api/breakers/report", json={
            "id": breaker_id,
            "success": True
        })
        assert r.status_code == 200
        assert r.json()["state"] == "CLOSED"
        assert r.json()["failure_count"] == 0

    def test_index_dashboard(self):
        """Verify index dashboard exists and contains all required chart canvases."""
        r = requests.get(f"{BASE_URL}/")
        assert r.status_code == 200
        html = r.text
        assert "closedChart" in html
        assert "openChart" in html
        assert "breakersChart" in html
