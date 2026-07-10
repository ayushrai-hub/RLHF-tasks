from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app/environment"))


def copy_worktree(tmp_path: Path) -> Path:
    work = tmp_path / "work"

    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in {"target", ".pytest_cache"}
            or name.endswith(".class")
            or name.endswith(".jar")
        }

    shutil.copytree(APP_DIR, work, ignore=ignore)
    return work


def run_sbt(work: Path, *tasks: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [str(work / "sbt"), *tasks],
        cwd=work,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"sbt {' '.join(tasks)} failed with exit {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    return result


def parse_properties(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        props[key.strip()] = value.strip()
    return props


def jar_names(jar_path: Path) -> set[str]:
    result = subprocess.run(
        ["jar", "tf", str(jar_path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert result.returncode == 0, f"jar tf failed for {jar_path}: {result.stderr}"
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def jar_read_text(jar_path: Path, entry: str) -> str:
    result = subprocess.run(
        ["unzip", "-p", str(jar_path), entry],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"unzip -p {entry} failed for {jar_path}: {result.stderr}"
    )
    return result.stdout


def sha256_file(path: Path) -> str:
    result = subprocess.run(
        ["sha256sum", str(path)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert result.returncode == 0, f"sha256sum failed for {path}: {result.stderr}"
    return result.stdout.split()[0]


def sha256_text(text: str) -> str:
    proc = subprocess.run(
        ["sha256sum"],
        input=text.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert proc.returncode == 0, (
        f"sha256sum stdin failed: {proc.stderr.decode('utf-8', 'replace')}"
    )
    return proc.stdout.decode("utf-8").split()[0]


def read_index_from_jar(jar_path: Path) -> tuple[dict[str, str], dict[str, str], str]:
    assert jar_path.exists(), f"missing published schema-index jar at {jar_path}"
    names = jar_names(jar_path)
    service_path = "META-INF/services/com.acme.rift.SchemaIndexProvider"
    assert service_path in names, (
        f"jar is missing ServiceLoader provider file {service_path}; has {sorted(n for n in names if n.startswith('META-INF/services/'))}"
    )
    service_text = jar_read_text(jar_path, service_path).strip()
    assert service_text.splitlines() == ["com.acme.generated.SchemaIndexProviderImpl"]
    index_text = jar_read_text(jar_path, "com/acme/generated/schema-index.properties")
    provenance_text = jar_read_text(
        jar_path, "com/acme/generated/schema-index-provenance.properties"
    )
    index = parse_properties(index_text)
    provenance = parse_properties(provenance_text)
    index_hash = sha256_text(index_text)
    return index, provenance, index_hash


def test_clean_publish_local_jar_contains_service_loader_index_and_provenance(
    tmp_path: Path,
) -> None:
    """Clean publish must create a jar whose ServiceLoader entry, descriptor index, and provenance agree."""
    work = copy_worktree(tmp_path)
    run_sbt(work, "clean", "publishLocal")
    index, provenance, _ = read_index_from_jar(
        work / "target/local-ivy/schema-index.jar"
    )

    assert index["descriptor.acme.activity.event.v2"] == "ActivityEvent"
    assert index["descriptor.acme.audit.envelope.v2"] == "AuditEnvelope"
    assert index["canonical.acme.activity.event.v2"] == "acme.activity.event.v2"
    assert index["canonical.acme.audit.envelope.v2"] == "acme.audit.envelope.v2"
    assert index["canonical.acme.user.event.v1"] == "acme.activity.event.v2"
    assert index["canonical.acme.audit.envelope.v1"] == "acme.audit.envelope.v2"
    assert (
        index["migration_source.acme.user.event.v1"]
        == "contracts/migrations/v1_to_v2_descriptor.map"
    )
    assert (
        index["migration_source.acme.audit.envelope.v1"]
        == "contracts/migrations/audit_v1_to_v2_descriptor.map"
    )

    assert provenance["service.type"] == "com.acme.rift.SchemaIndexProvider"
    assert (
        provenance["service.provider"] == "com.acme.generated.SchemaIndexProviderImpl"
    )
    assert provenance["index.resource"] == "com/acme/generated/schema-index.properties"
    for rel in [
        "contracts/activity.rift",
        "contracts/envelope.rift",
        "contracts/migrations/v1_to_v2_descriptor.map",
        "contracts/migrations/audit_v1_to_v2_descriptor.map",
        "project/service-loader.properties",
        "project/package-layout.properties",
        "project/descriptor-provenance.policy",
    ]:
        sha_key = f"input.{rel}.sha256"
        bytes_key = f"input.{rel}.bytes"
        assert re.fullmatch(r"[0-9a-f]{64}", provenance.get(sha_key, "")), (
            f"missing sha256 provenance for {rel}"
        )
        assert provenance.get(bytes_key, "").isdigit(), (
            f"missing byte provenance for {rel}"
        )
        actual = sha256_file(work / rel)
        assert provenance[sha_key] == actual


def test_consumer_roundtrip_uses_published_local_jar_for_legacy_and_current_fixtures(
    tmp_path: Path,
) -> None:
    """The consumer report must come from the published local jar and canonicalize all visible v1/v2 fixtures."""
    work = copy_worktree(tmp_path)
    run_sbt(work, "clean", "publishLocal", "consumerRoundTrip")
    report_path = work / "target/consumer/roundtrip-report.json"
    assert report_path.exists(), (
        "consumerRoundTrip did not produce the visible roundtrip report"
    )
    report = json.loads(report_path.read_text())
    assert report["schema_index_jar"] == "target/local-ivy/schema-index.jar"
    assert report["provider_count"] == 1
    assert report["canonical_descriptor_count"] >= 2
    assert report["all_ok"] is True
    rows = {row["fixture_id"]: row for row in report["roundtrips"]}
    assert rows["legacy-user-event-001"]["input_descriptor"] == "acme.user.event.v1"
    assert (
        rows["legacy-user-event-001"]["canonical_descriptor"]
        == "acme.activity.event.v2"
    )
    assert (
        rows["legacy-audit-envelope-001"]["input_descriptor"]
        == "acme.audit.envelope.v1"
    )
    assert (
        rows["legacy-audit-envelope-001"]["canonical_descriptor"]
        == "acme.audit.envelope.v2"
    )
    assert (
        rows["current-activity-001"]["canonical_descriptor"] == "acme.activity.event.v2"
    )
    assert (
        rows["current-envelope-001"]["canonical_descriptor"] == "acme.audit.envelope.v2"
    )


def test_incremental_migration_map_change_matches_clean_regeneration(
    tmp_path: Path,
) -> None:
    """An incremental migration-map edit must regenerate the same index and provenance as a clean rebuild."""
    work = copy_worktree(tmp_path)
    run_sbt(work, "clean", "publishLocal")

    migration = work / "contracts/migrations/v1_to_v2_descriptor.map"
    migration.write_text(
        migration.read_text() + "\nacme.mobile.user_event.v1 = acme.activity.event.v2\n"
    )
    new_fixture = work / "consumer/fixtures/mobile-legacy-user-event.json"
    new_fixture.write_text(
        json.dumps(
            {
                "fixture_id": "mobile-legacy-user-event-001",
                "descriptor": "acme.mobile.user_event.v1",
                "expected_descriptor": "acme.activity.event.v2",
                "event_id": "evt-mobile-legacy-001",
                "account_id": "acct-9",
                "activity_kind": "mobile-login",
            },
            indent=2,
        )
        + "\n"
    )
    consumer_build = work / "consumer/consumer.build"
    lines = consumer_build.read_text().splitlines()
    consumer_build.write_text(
        "\n".join(
            line + " consumer/fixtures/mobile-legacy-user-event.json"
            if line.startswith("roundtrip_fixtures=")
            else line
            for line in lines
        )
        + "\n"
    )

    run_sbt(work, "publishLocal", "consumerRoundTrip")
    incr_index, incr_prov, incr_hash = read_index_from_jar(
        work / "target/local-ivy/schema-index.jar"
    )
    incr_report = json.loads(
        (work / "target/consumer/roundtrip-report.json").read_text()
    )
    assert incr_index["canonical.acme.mobile.user_event.v1"] == "acme.activity.event.v2"
    assert any(
        row["fixture_id"] == "mobile-legacy-user-event-001" and row["ok"]
        for row in incr_report["roundtrips"]
    )

    run_sbt(work, "clean", "publishLocal", "consumerRoundTrip")
    clean_index, clean_prov, clean_hash = read_index_from_jar(
        work / "target/local-ivy/schema-index.jar"
    )
    assert clean_hash == incr_hash
    assert clean_index == incr_index
    assert (
        clean_prov["input.contracts/migrations/v1_to_v2_descriptor.map.sha256"]
        == incr_prov["input.contracts/migrations/v1_to_v2_descriptor.map.sha256"]
    )


def test_static_generated_artifact_patch_is_overwritten_by_clean_rebuild(
    tmp_path: Path,
) -> None:
    """A bogus prewritten generated artifact must be overwritten by provenance-driven clean regeneration."""
    work = copy_worktree(tmp_path)
    generated = work / "target/schema-index/classes/com/acme/generated"
    generated.mkdir(parents=True, exist_ok=True)
    (generated / "schema-index.properties").write_text(
        "canonical.acme.user.event.v1=static-shortcut" + "\n"
    )

    run_sbt(work, "clean", "publishLocal", "consumerRoundTrip")
    index, provenance, _ = read_index_from_jar(
        work / "target/local-ivy/schema-index.jar"
    )
    assert index["canonical.acme.user.event.v1"] == "acme.activity.event.v2"
    assert index["canonical.acme.audit.envelope.v1"] == "acme.audit.envelope.v2"
    assert "static-shortcut" not in "\n".join(f"{k}={v}" for k, v in index.items())
    assert provenance["service.type"] == "com.acme.rift.SchemaIndexProvider"
