import json
import os
import subprocess
from pathlib import Path

APP_ROOT = Path(os.environ.get("APP_ROOT", "/app"))
CLI = APP_ROOT / "bin" / "audit-cname-chains"


def run_cli(config, zones, services, out):
    env = os.environ.copy()
    env["APP_ROOT"] = str(APP_ROOT)
    result = subprocess.run(
        [str(CLI), "--config", str(config), "--zones", str(zones), "--services", str(services), "--out", str(out)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((Path(out) / "cname_chain_report.json").read_text())
    warnings = json.loads((Path(out) / "warnings.json").read_text())
    return report, warnings


def bundled_paths(tmp_path):
    out = tmp_path / "out"
    return APP_ROOT / "config" / "audit-policy.json", APP_ROOT / "fixtures" / "zones", APP_ROOT / "fixtures" / "service-catalog.json", out


def by_chain(report):
    return {row["chain_id"]: row for row in report["chains"]}


def test_bundled_report_summarizes_chains_findings_warnings_and_schema(tmp_path):
    """The bundled audit must emit the documented report schema, cross-output counts, and key loop/stale/ownership findings."""
    config, zones, services, out = bundled_paths(tmp_path)
    report, warnings = run_cli(config, zones, services, out)

    assert set(report) == {"generated_at", "summary", "chains", "findings"}
    assert report["generated_at"] == "2026-04-15T00:00:00Z"
    assert report["summary"] == {
        "chains_total": 10,
        "findings_total": 8,
        "warnings_total": 3,
        "loops": 3,
        "stale_services": 3,
        "ownership_gaps": 2,
        "max_chain_length": 3,
    }
    assert len(warnings) == report["summary"]["warnings_total"]
    assert len(report["findings"]) == report["summary"]["findings_total"]

    chains = by_chain(report)
    assert chains["api.example.com"]["target"] == "api-green.internal.example.net"
    assert chains["api.example.com"]["service_id"] == "svc-api-green"
    assert chains["marketing.example.com"]["terminal"] == "old.marketing-vendor.net"
    assert chains["marketing.example.com"]["hops"] == [
        {"name": "marketing.example.com", "target": "vanity.example.com"},
        {"name": "vanity.example.com", "target": "old.marketing-vendor.net"},
    ]
    assert chains["loop-a.example.com"]["loop"] is True
    assert chains["loop-a.example.com"]["status"] == "loop"

    finding_keys = {(f["code"], f["chain_id"], f["detail"]) for f in report["findings"]}
    assert ("loop_detected", "loop-a.example.com", "CNAME loop detected: loop-a.example.com -> loop-b.example.com -> loop-c.example.com -> loop-a.example.com") in finding_keys
    assert ("stale_service", "legacy.example.com", "terminal legacy.cdn-vendor.net resolves to stale service svc-legacy-cdn") in finding_keys
    assert ("ownership_gap", "orphan.example.com", "service svc-orphan has no owner") in finding_keys
    assert ("ownership_gap", "unknown.stage.example.com", "terminal not-in-catalog.external.net has no catalog owner") in finding_keys


def test_duplicate_tiebreaker_warning_source_metadata_and_sorting(tmp_path):
    """Duplicate CNAME rows must use priority/source/line tie-breakers and warning metadata must refer to discarded records."""
    config, zones, services, out = bundled_paths(tmp_path)
    report, warnings = run_cli(config, zones, services, out)

    api = by_chain(report)["api.example.com"]
    assert api["source_path"] == "prod/override.jsonl"
    assert api["source_line"] == 1
    assert api["target"] == "api-green.internal.example.net"

    duplicate = [w for w in warnings if w["code"] == "duplicate_cname"]
    assert duplicate == [{
        "code": "duplicate_cname",
        "severity": "warning",
        "subject_id": "api.example.com",
        "source_path": "prod/core.jsonl",
        "source_line": 2,
        "detail": "duplicate CNAME api.example.com; kept prod/override.jsonl:1",
    }]

    warning_sort_keys = [(w["code"], w["subject_id"], w["source_path"], w["source_line"], w["detail"]) for w in warnings]
    assert warning_sort_keys == sorted(warning_sort_keys)
    finding_sort_keys = [(f["code"], f["chain_id"], f["source_path"], f["source_line"], f["detail"]) for f in report["findings"]]
    assert finding_sort_keys == sorted(finding_sort_keys)


def test_malformed_rows_preserve_valid_peers_and_exact_invalid_warning_details(tmp_path):
    """Invalid JSON and invalid parsed CNAME rows must warn without blocking neighboring valid chains."""
    config, zones, services, out = bundled_paths(tmp_path)
    report, warnings = run_cli(config, zones, services, out)

    chains = by_chain(report)
    assert "legacy.example.com" in chains
    assert "orphan.example.com" in chains
    assert "missing-target.example.com" not in chains

    invalid_json = [w for w in warnings if w["code"] == "invalid_json"]
    assert invalid_json == [{
        "code": "invalid_json",
        "severity": "error",
        "subject_id": "",
        "source_path": "prod/core.jsonl",
        "source_line": 3,
        "detail": "invalid JSON at prod/core.jsonl:3",
    }]
    invalid_cname = [w for w in warnings if w["code"] == "invalid_cname"]
    assert invalid_cname == [{
        "code": "invalid_cname",
        "severity": "error",
        "subject_id": "missing-target.example.com",
        "source_path": "prod/override.jsonl",
        "source_line": 7,
        "detail": "invalid CNAME record missing target",
    }]


def test_rerun_removes_stale_outputs_and_is_byte_stable(tmp_path):
    """Every run must clean stale output files and produce byte-stable JSON outputs."""
    config, zones, services, out = bundled_paths(tmp_path)
    out.mkdir(parents=True)
    (out / "old-report.json").write_text("stale")

    run_cli(config, zones, services, out)
    first_report = (out / "cname_chain_report.json").read_bytes()
    first_warnings = (out / "warnings.json").read_bytes()
    assert sorted(p.name for p in out.iterdir()) == ["cname_chain_report.json", "warnings.json"]

    run_cli(config, zones, services, out)
    assert (out / "cname_chain_report.json").read_bytes() == first_report
    assert (out / "warnings.json").read_bytes() == first_warnings
    assert sorted(p.name for p in out.iterdir()) == ["cname_chain_report.json", "warnings.json"]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n")


def test_dynamic_fixture_aliases_duplicate_full_tiebreakers_loops_and_valid_peer_preservation(tmp_path):
    """A generated fixture prevents hardcoded bundled answers while exercising aliases, duplicate ties, loops, and malformed-row preservation."""
    config = tmp_path / "config.json"
    services = tmp_path / "services.json"
    zones = tmp_path / "zones"
    out = tmp_path / "out"
    write_json(config, {"as_of": "2026-04-15T00:00:00Z", "max_hops": 6, "service_aliases": {"retired.alias.net": "svc-retired"}})
    write_json(services, {"services": [
        {"service_id": "svc-active-a", "domains": ["active-a.example.net"], "owner": "team-a", "status": "active", "retired_at": ""},
        {"service_id": "svc-active-b", "domains": ["active-b.example.net"], "owner": "team-b", "status": "active", "retired_at": ""},
        {"service_id": "svc-retired", "domains": ["retired.alias.net"], "owner": "legacy", "status": "active", "retired_at": "2026-01-01"},
    ]})
    (zones / "a.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (zones / "a.jsonl").write_text("\n".join([
        '{"zone":"example.net","name":"tie.example.net","type":"CNAME","target":"active-a.example.net","priority":5}',
        '{"zone":"example.net","name":"root.example.net","type":"CNAME","target":"mid.example.net","priority":1}',
        '{"zone":"example.net","name":"mid.example.net","type":"CNAME","target":"retired.alias.net","priority":1}',
        '{"zone":"example.net","name":"cycle-a.example.net","type":"CNAME","target":"cycle-b.example.net","priority":1}',
        '{"zone":"example.net","name":"cycle-b.example.net","type":"CNAME","target":"cycle-a.example.net","priority":1}',
        '{not json}',
        '{"zone":"example.net","name":"peer.example.net","type":"CNAME","target":"active-b.example.net","priority":1}',
    ]) + "\n")
    (zones / "b.jsonl").write_text('{"zone":"example.net","name":"tie.example.net","type":"CNAME","target":"active-b.example.net","priority":5}\n')

    report, warnings = run_cli(config, zones, services, out)
    chains = by_chain(report)
    assert chains["tie.example.net"]["target"] == "active-a.example.net"
    assert chains["tie.example.net"]["source_path"] == "a.jsonl"
    assert chains["root.example.net"]["terminal"] == "retired.alias.net"
    assert chains["root.example.net"]["service_id"] == "svc-retired"
    assert chains["peer.example.net"]["service_id"] == "svc-active-b"
    assert chains["cycle-a.example.net"]["loop"] is True

    assert any(w["code"] == "duplicate_cname" and w["detail"] == "duplicate CNAME tie.example.net; kept a.jsonl:1" for w in warnings)
    assert any(w["code"] == "invalid_json" and w["detail"] == "invalid JSON at a.jsonl:6" for w in warnings)
    assert any(f["code"] == "stale_service" and f["chain_id"] == "root.example.net" and f["detail"] == "terminal retired.alias.net resolves to stale service svc-retired" for f in report["findings"])
    assert any(f["code"] == "loop_detected" and f["chain_id"] == "cycle-a.example.net" for f in report["findings"])


def test_dynamic_max_hops_stops_before_terminal_resolution(tmp_path):
    """A generated chain that exceeds max_hops must stop at the capped terminal and stay non-loop/unknown."""
    config = tmp_path / "config.json"
    services = tmp_path / "services.json"
    zones = tmp_path / "zones"
    out = tmp_path / "out"
    write_json(config, {"as_of": "2026-04-15T00:00:00Z", "max_hops": 2, "service_aliases": {}})
    write_json(services, {"services": [
        {"service_id": "svc-final", "domains": ["final.example.net"], "owner": "team-final", "status": "active", "retired_at": ""},
    ]})
    zones.mkdir(parents=True, exist_ok=True)
    (zones / "chain.jsonl").write_text("\n".join([
        '{"zone":"example.net","name":"a.example.net","type":"CNAME","target":"b.example.net","priority":1}',
        '{"zone":"example.net","name":"b.example.net","type":"CNAME","target":"c.example.net","priority":1}',
        '{"zone":"example.net","name":"c.example.net","type":"CNAME","target":"final.example.net","priority":1}',
    ]) + "\n")

    report, warnings = run_cli(config, zones, services, out)
    chains = by_chain(report)
    capped = chains["a.example.net"]

    assert capped["hops"] == [
        {"name": "a.example.net", "target": "b.example.net"},
        {"name": "b.example.net", "target": "c.example.net"},
    ]
    assert capped["terminal"] == "c.example.net"
    assert capped["loop"] is False
    assert capped["service_id"] == ""
    assert capped["owner"] == ""
    assert capped["status"] == "unknown"
    assert any(
        f["code"] == "ownership_gap"
        and f["chain_id"] == "a.example.net"
        and f["detail"] == "terminal c.example.net has no catalog owner"
        for f in report["findings"]
    )
    assert warnings == []


def test_dynamic_duplicate_source_line_tiebreaker_and_warning(tmp_path):
    """When duplicate priority and source_path are tied, the lower physical source_line must win and the later row must warn."""
    config = tmp_path / "config.json"
    services = tmp_path / "services.json"
    zones = tmp_path / "zones"
    out = tmp_path / "out"
    write_json(config, {"as_of": "2026-04-15T00:00:00Z", "max_hops": 4, "service_aliases": {}})
    write_json(services, {"services": [
        {"service_id": "svc-first", "domains": ["first.example.net"], "owner": "team-first", "status": "active", "retired_at": ""},
        {"service_id": "svc-second", "domains": ["second.example.net"], "owner": "team-second", "status": "active", "retired_at": ""},
    ]})
    zones.mkdir(parents=True, exist_ok=True)
    (zones / "dupes.jsonl").write_text("\n".join([
        '{"zone":"example.net","name":"line-tie.example.net","type":"CNAME","target":"first.example.net","priority":7}',
        '{"zone":"example.net","name":"line-tie.example.net","type":"CNAME","target":"second.example.net","priority":7}',
    ]) + "\n")

    report, warnings = run_cli(config, zones, services, out)
    chains = by_chain(report)
    winner = chains["line-tie.example.net"]

    assert winner["target"] == "first.example.net"
    assert winner["service_id"] == "svc-first"
    assert winner["source_path"] == "dupes.jsonl"
    assert winner["source_line"] == 1
    assert warnings == [{
        "code": "duplicate_cname",
        "severity": "warning",
        "subject_id": "line-tie.example.net",
        "source_path": "dupes.jsonl",
        "source_line": 2,
        "detail": "duplicate CNAME line-tie.example.net; kept dupes.jsonl:1",
    }]


def test_loop_suppresses_service_lookup_and_unknown_suppresses_stale_service(tmp_path):
    """Evaluation-order rules must suppress downstream findings for loops and unknown terminals."""
    config, zones, services, out = bundled_paths(tmp_path)
    report, _ = run_cli(config, zones, services, out)

    loop_findings = [f for f in report["findings"] if f["chain_id"] == "loop-a.example.com"]
    assert [f["code"] for f in loop_findings] == ["loop_detected"]
    assert loop_findings[0]["service_id"] == ""
    assert by_chain(report)["loop-a.example.com"]["service_id"] == ""

    unknown_findings = [f for f in report["findings"] if f["chain_id"] == "unknown.stage.example.com"]
    assert [f["code"] for f in unknown_findings] == ["ownership_gap"]
    assert unknown_findings[0]["detail"] == "terminal not-in-catalog.external.net has no catalog owner"


def test_dynamic_hidden_zone_paths_are_excluded_without_warnings(tmp_path):
    """Hidden directories or hidden JSONL files under the zones tree must be skipped completely."""
    config = tmp_path / "config.json"
    services = tmp_path / "services.json"
    zones = tmp_path / "zones"
    out = tmp_path / "out"
    write_json(config, {"as_of": "2026-04-15T00:00:00Z", "max_hops": 4, "service_aliases": {}})
    write_json(services, {"services": [
        {"service_id": "svc-visible", "domains": ["visible-target.example.net"], "owner": "dns-team", "status": "active", "retired_at": ""},
        {"service_id": "svc-hidden", "domains": ["hidden.example.net"], "owner": "shadow-team", "status": "retired", "retired_at": "2025-01-01"},
    ]})
    zones.mkdir(parents=True, exist_ok=True)
    (zones / "visible.jsonl").write_text(
        '{"zone":"example.net","name":"visible.example.net","type":"CNAME","target":"visible-target.example.net","priority":1}\n'
    )
    hidden_dir = zones / ".archive"
    hidden_dir.mkdir(parents=True)
    (hidden_dir / "hidden.jsonl").write_text(
        '{not json}\n'
        '{"zone":"example.net","name":"hidden-dir.example.net","type":"CNAME","target":"hidden.example.net","priority":9}\n'
    )
    (zones / ".hidden.jsonl").write_text(
        '{"zone":"example.net","name":"hidden-file.example.net","type":"CNAME","target":"hidden.example.net","priority":9}\n'
    )

    report, warnings = run_cli(config, zones, services, out)
    chains = by_chain(report)

    assert sorted(chains) == ["visible.example.net"]
    assert chains["visible.example.net"]["service_id"] == "svc-visible"
    assert report["summary"]["chains_total"] == 1
    assert report["summary"]["warnings_total"] == 0
    assert report["findings"] == []
    assert warnings == []


def test_dynamic_service_aliases_take_precedence_over_catalog_domains(tmp_path):
    """A terminal listed in service_aliases must resolve to that service before catalog domain matching."""
    config = tmp_path / "config.json"
    services = tmp_path / "services.json"
    zones = tmp_path / "zones"
    out = tmp_path / "out"
    write_json(config, {
        "as_of": "2026-04-15T00:00:00Z",
        "max_hops": 4,
        "service_aliases": {"shared.example.net": "svc-alias"},
    })
    write_json(services, {"services": [
        {"service_id": "svc-domain", "domains": ["shared.example.net"], "owner": "domain-team", "status": "retired", "retired_at": "2025-01-01"},
        {"service_id": "svc-alias", "domains": ["alias-only.example.net"], "owner": "alias-team", "status": "active", "retired_at": ""},
    ]})
    zones.mkdir(parents=True, exist_ok=True)
    (zones / "alias.jsonl").write_text(
        '{"zone":"example.net","name":"app.example.net","type":"CNAME","target":"shared.example.net","priority":1}\n'
    )

    report, warnings = run_cli(config, zones, services, out)
    chain = by_chain(report)["app.example.net"]

    assert chain["terminal"] == "shared.example.net"
    assert chain["service_id"] == "svc-alias"
    assert chain["owner"] == "alias-team"
    assert chain["status"] == "active"
    assert report["summary"]["findings_total"] == 0
    assert report["findings"] == []
    assert warnings == []
