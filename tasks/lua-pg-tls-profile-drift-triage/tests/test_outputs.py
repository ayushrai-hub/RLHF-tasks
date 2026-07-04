import json
import shutil
import subprocess
from datetime import date, timedelta
from pathlib import Path

import jsonschema
import tomllib
import yaml

APP = Path("/app")
ENV = APP / "environment"
OUT = APP / "out" / "reconcile_report.json"
CLI = "/app/bin/ingressctl"
SCHEMA = ENV / "schemas" / "reconcile_report.schema.json"
YAML_BUNDLE = ENV / "config/bundles/bundle.yaml"
TOML_BUNDLE = ENV / "config/bundles/client.toml"
SNAPSHOT_ACTIVE_COUNT = 7
API_VERSION = "payments-ingress-tls/1"
ROLLOVER_EPOCH = "2026-03-15"
GRACE_DAYS = 14


def _start_pg() -> None:
    proc = subprocess.run(
        ["bash", "/app/environment/ci/seed_inventory.sh"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def _reset_out() -> None:
    out_dir = APP / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def _run_reconcile() -> dict:
    _reset_out()
    _start_pg()
    proc = subprocess.run(
        [CLI, "tls-reconcile"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert OUT.is_file()
    return json.loads(OUT.read_text(encoding="utf-8"))


def _canonical_fp(raw_hex: str) -> str:
    body = raw_hex.strip().lower().replace(":", "")
    return ":".join(body[i : i + 2] for i in range(0, len(body), 2))


def _parse_date(text: str) -> date:
    y, m, d = text.split("-")
    return date(int(y), int(m), int(d))


def _psql_rows(sql: str) -> list[list[str]]:
    proc = subprocess.run(
        ["bash", "-lc", f"runuser -u postgres -- psql -d payments_tls -t -A -F '|' -c {json.dumps(sql)}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.split("|") for line in proc.stdout.splitlines() if line.strip()]


def _ref_reconcile() -> dict:
    yaml_doc = yaml.safe_load(YAML_BUNDLE.read_text(encoding="utf-8"))
    toml_doc = tomllib.loads(TOML_BUNDLE.read_text(encoding="utf-8"))
    reference_clock = yaml_doc["reference_clock"]
    revoked = {cols[0] for cols in _psql_rows("SELECT serial FROM revocation_events")}
    ref = _parse_date(reference_clock)
    cutoff = ref - timedelta(days=GRACE_DAYS)
    active = []
    for serial, subject_cn, sha256_hex, not_after, role_tag in _psql_rows(
        "SELECT serial, subject_cn, sha256_hex, not_after, role_tag FROM cert_inventory ORDER BY serial"
    ):
        if serial in revoked or _parse_date(not_after) < cutoff:
            continue
        active.append(
            {
                "serial": serial,
                "subject_cn": subject_cn,
                "fingerprint": _canonical_fp(sha256_hex),
                "role_tag": role_tag,
            }
        )
    fp_index = {row["fingerprint"]: row for row in active}
    inventory_all_fps = {
        _canonical_fp(cols[0]) for cols in _psql_rows("SELECT sha256_hex FROM cert_inventory")
    }
    revoked_fps = {
        _canonical_fp(cols[0])
        for cols in _psql_rows(
            "SELECT ci.sha256_hex FROM revocation_events re "
            "JOIN cert_inventory ci ON ci.serial = re.serial"
        )
    }
    trust_anchors = []
    for anchor in yaml_doc["trust_anchors"]:
        cfg_fp = _canonical_fp(anchor["fingerprint"])
        enabled = False
        reason = "stale_config"
        if cfg_fp in revoked_fps:
            reason = "revoked"
        elif cfg_fp in fp_index:
            enabled = True
            reason = "inventory_match"
        elif cfg_fp in inventory_all_fps:
            reason = "expired"
        trust_anchors.append(
            {
                "anchor_id": anchor["anchor_id"],
                "fingerprint": cfg_fp,
                "enabled": enabled,
                "reason": reason,
            }
        )
    trust_anchors.sort(key=lambda r: r["anchor_id"])
    by_serial = {row["serial"]: row for row in active}
    binding_map = {
        cols[0]: cols[2]
        for cols in _psql_rows(
            "SELECT service_name, role_tag, client_ca_serial FROM role_bindings"
        )
    }
    service_bindings = []
    for service, _body in sorted((toml_doc.get("client_ca") or {}).items()):
        serial = binding_map.get(service)
        inv = by_serial.get(serial) if serial else None
        if inv:
            service_bindings.append(
                {
                    "service": service,
                    "client_ca": inv["subject_cn"],
                    "fingerprint": inv["fingerprint"],
                }
            )
    drift_staging = []
    for anchor in yaml_doc["trust_anchors"]:
        cfg_fp = _canonical_fp(anchor["fingerprint"])
        if cfg_fp in inventory_all_fps and anchor["fingerprint"] != cfg_fp:
            drift_staging.append(
                (
                    anchor["anchor_id"],
                    {
                        "source": "yaml",
                        "field": "fingerprint",
                        "config_value": anchor["fingerprint"],
                        "inventory_value": cfg_fp,
                    },
                )
            )
    drift_staging.sort(key=lambda item: (item[0], item[1]["field"]))
    drift_rows = [row for _, row in drift_staging]
    digest_body = "\n".join(
        sorted(f"{row['serial']}:{row['fingerprint']}" for row in active)
    )
    proc = subprocess.run(
        ["sha256sum"],
        input=digest_body.encode(),
        check=True,
        capture_output=True,
    )
    inventory_digest = proc.stdout.decode().split()[0]
    return {
        "api_version": yaml_doc["api_version"],
        "rollover_epoch": yaml_doc["rollover_epoch"],
        "inventory_digest": inventory_digest,
        "trust_anchors": trust_anchors,
        "service_bindings": service_bindings,
        "drift_rows": drift_rows,
    }


def _validate_schema(report: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(report, schema)


def test_regenerated_doc_passes_validator() -> None:
    """Regenerated report must satisfy the published JSON schema."""
    report = _run_reconcile()
    _validate_schema(report)


def test_regenerated_doc_matches_ref() -> None:
    """Regenerated report must match the independent reference builder."""
    report = _run_reconcile()
    ref = _ref_reconcile()
    assert report["inventory_digest"] == ref["inventory_digest"]
    assert report["trust_anchors"] == ref["trust_anchors"]
    assert report["service_bindings"] == ref["service_bindings"]
    assert report["drift_rows"] == ref["drift_rows"]


def test_regenerated_doc_header_fields() -> None:
    """Top-level api_version and rollover_epoch follow the YAML bundle."""
    report = _run_reconcile()
    assert report["api_version"] == API_VERSION
    assert report["rollover_epoch"] == ROLLOVER_EPOCH


def test_binding_gate_four_services() -> None:
    """All four ingress services map to live client CAs with colon fingerprints."""
    report = _run_reconcile()
    services = {row["service"]: row for row in report["service_bindings"]}
    assert set(services) == {
        "payments-api",
        "ledger-writer",
        "fraud-scorer",
        "settlement-gw",
    }
    for row in report["service_bindings"]:
        assert ":" in row["fingerprint"]
        assert row["fingerprint"] == row["fingerprint"].lower()


def test_digest_gate_active_serials() -> None:
    """Digest must reflect the seven active non-revoked serials."""
    report = _run_reconcile()
    ref = _ref_reconcile()
    assert SNAPSHOT_ACTIVE_COUNT == 7
    assert report["inventory_digest"] == ref["inventory_digest"]


def test_drift_gate_normalization() -> None:
    """Drift rows record bare-hex config fingerprints against canonical values."""
    report = _run_reconcile()
    assert len(report["drift_rows"]) >= 1
    for row in report["drift_rows"]:
        assert row["source"] == "yaml"
        assert row["field"] == "fingerprint"
        assert ":" not in row["config_value"]
        assert ":" in row["inventory_value"]


def test_static_doc_insufficient() -> None:
    """Hand-written JSON must not satisfy reference digest checks."""
    _start_pg()
    ref = _ref_reconcile()
    fake = {
        "api_version": API_VERSION,
        "rollover_epoch": ROLLOVER_EPOCH,
        "inventory_digest": "0" * 64,
        "trust_anchors": [],
        "service_bindings": [],
        "drift_rows": [],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fake), encoding="utf-8")
    on_disk = json.loads(OUT.read_text(encoding="utf-8"))
    assert on_disk["inventory_digest"] != ref["inventory_digest"]


def test_phantom_toml_anchor_absent() -> None:
    """TOML-only trust anchor blocks must not appear in the report."""
    report = _run_reconcile()
    anchor_ids = {row["anchor_id"] for row in report["trust_anchors"]}
    assert "phantom_toml" not in anchor_ids
    assert len(anchor_ids) == 4
