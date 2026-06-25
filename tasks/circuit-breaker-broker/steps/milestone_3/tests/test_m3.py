import os
import json
import requests

BASE_URL = "http://127.0.0.1:8080"
STATE_PATH = "/app/state/state.json"

class TestMilestone3:
    def test_state_persistence_file(self):
        """Verify that state.json is automatically persisted on disk."""
        # Trigger mutation
        requests.post(f"{BASE_URL}/api/breakers", json={
            "id": "persisted_breaker_1",
            "policy": "simple",
            "failure_threshold": 3,
            "recovery_timeout_us": 50000
        })
        assert os.path.exists(STATE_PATH)
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
        assert data["schema_version"] == 1
        assert "persisted_breaker_1" in data["breakers"]

    def test_integrity_endpoint(self):
        """Verify state integrity endpoint calculates SHA-256 and records state shape."""
        r = requests.get(f"{BASE_URL}/api/state/integrity")
        assert r.status_code == 200
        data = r.json()
        assert data["state_file_exists"] is True
        assert len(data["sha256"]) == 64
        assert "snapshot" in data
        assert data["snapshot"]["breakers"] > 0

    def test_alert_threshold_registration(self):
        """Verify trip alert thresholds can be registered, retrieved, and cleared."""
        r = requests.post(f"{BASE_URL}/api/alerts/thresholds", json={
            "breaker_id": "persisted_breaker_1",
            "max_denial_count": 5,
            "window_us": 10000000
        })
        assert r.status_code == 200
        assert r.json()["max_denial_count"] == 5
        
        # Get thresholds
        r_get = requests.get(f"{BASE_URL}/api/alerts/thresholds")
        assert r_get.json()["persisted_breaker_1"]["max_denial_count"] == 5
        assert r_get.json()["persisted_breaker_1"]["window_us"] == 10000000

    def test_alert_firing_logic(self):
        """Verify alerts fire when denial count exceeds configured thresholds after 30 attempts."""
        # Register a new breaker
        breaker_id = "alert_breaker"
        requests.post(f"{BASE_URL}/api/breakers", json={
            "id": breaker_id,
            "policy": "simple",
            "failure_threshold": 1,
            "recovery_timeout_us": 100000000
        })
        # Register threshold
        requests.post(f"{BASE_URL}/api/alerts/thresholds", json={
            "breaker_id": breaker_id,
            "max_denial_count": 10,
            "window_us": 50000000
        })
        
        # Trip the breaker so subsequent checks return allowed: false
        requests.post(f"{BASE_URL}/api/breakers/report", json={"id": breaker_id, "success": False})
        
        # Fire 35 check requests (total 35 denials, threshold is 10)
        # Advance time slightly to have distinct timestamps
        for i in range(35):
            requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 1})
            requests.post(f"{BASE_URL}/api/check", json={"breaker_id": breaker_id})
            
        # Get alerts
        r = requests.get(f"{BASE_URL}/api/alerts")
        assert r.status_code == 200
        alerts = r.json()["alerts"]
        assert len(alerts) > 0
        assert any(a["breaker_id"] == breaker_id for a in alerts)
        
        target_alert = next(a for a in alerts if a["breaker_id"] == breaker_id)
        assert target_alert["threshold"] == 10
        assert target_alert["denial_count"] > 10
        assert target_alert["severity"] in ("low", "medium", "high", "critical")

    def test_alert_cooldown(self):
        """Verify alert cooldown blocks firing duplicate alerts too quickly."""
        r_pre = requests.get(f"{BASE_URL}/api/alerts")
        count_pre = len(r_pre.json()["alerts"])
        
        # Advance clock by 1 second (cooldown is 60 seconds)
        requests.post(f"{BASE_URL}/api/admin/advance", json={"micros": 1000000})
        requests.post(f"{BASE_URL}/api/check", json={"breaker_id": "alert_breaker"})
        
        r_post = requests.get(f"{BASE_URL}/api/alerts")
        count_post = len(r_post.json()["alerts"])
        assert count_pre == count_post  # No new alert should fire

    def test_clear_alerts(self):
        """Verify alert buffer can be cleared."""
        r = requests.post(f"{BASE_URL}/api/alerts/clear")
        assert r.status_code == 200
        assert r.json() == {"cleared": True}
        
        # Check alerts log is empty
        r_alerts = requests.get(f"{BASE_URL}/api/alerts")
        assert r_alerts.json()["count"] == 0

    def test_state_reload_integrity(self):
        """Verify reload-state endpoint recovers state correctly."""
        # Clear alert thresholds in-memory and reload from disk
        r = requests.post(f"{BASE_URL}/api/admin/reload-state")
        assert r.status_code == 200
        assert r.json()["reloaded"] is True
        
        # Check that thresholds are loaded back
        r_get = requests.get(f"{BASE_URL}/api/alerts/thresholds")
        assert "alert_breaker" in r_get.json()

    def test_state_reload_empty_if_missing(self):
        """Verify broker initializes to empty state if state file is missing on reload."""
        if os.path.exists(STATE_PATH):
            os.remove(STATE_PATH)
            
        r = requests.post(f"{BASE_URL}/api/admin/reload-state")
        assert r.status_code == 200
        
        # Clock should reset to 0
        r_now = requests.get(f"{BASE_URL}/api/now")
        assert r_now.json()["now_us"] == 0
        
        # Thresholds should be empty
        r_get = requests.get(f"{BASE_URL}/api/alerts/thresholds")
        assert len(r_get.json()) == 0

    def test_schema_conformance(self):
        """Verify persisted JSON format follows state_snapshot.schema.json structure rules."""
        # Create breaker to trigger file persist
        requests.post(f"{BASE_URL}/api/breakers", json={
            "id": "schema_test",
            "policy": "simple",
            "failure_threshold": 3,
            "recovery_timeout_us": 100000
        })
        
        with open(STATE_PATH, "r") as f:
            data = json.load(f)
            
        required_keys = [
            "schema_version", "now_us", "breakers", "audit", "audit_id_counter",
            "alert_thresholds", "alerts", "alert_id_counter", "last_alert_at_us"
        ]
        for key in required_keys:
            assert key in data
            
        assert data["schema_version"] == 1
        assert isinstance(data["breakers"], dict)
        assert isinstance(data["audit"], list)
        assert isinstance(data["alerts"], list)
        for key in data.keys():
            assert key in required_keys
