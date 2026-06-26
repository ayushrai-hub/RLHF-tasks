"""Verifier for the Maven dependency convergence auditor task."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from collections import OrderedDict, defaultdict
from functools import cmp_to_key
from pathlib import Path

APP = Path(os.environ.get("APP_DIR", "/app"))
OUT = APP / "out"
FIXTURES = APP / "fixtures"
JSON_OUT = OUT / "dependency-convergence.json"
CSV_OUT = OUT / "dependency-audit.csv"

EXPECTED_FIXTURE_TREE_SHA256 = "4408be1d4a607f0612f6381eba4df983fa7ee32aa75b2e8d6caa1d62d203adcc"
REASON_ORDER = [
    "version_conflict",
    "managed_version_mismatch",
    "below_minimum_version",
    "relocation_notice",
    "alignment_drift",
    "banned_license",
    "critical_cve",
    "snapshot_version",
    "range_unpinned",
]
BLOCK_REASONS = {"managed_version_mismatch", "below_minimum_version", "banned_license", "critical_cve"}
ARTIFACT_KEYS = ["coordinate", "selectedVersion", "status", "modules", "versions", "reasons", "effectiveScopes", "highestCvss"]
MODULE_KEYS = ["module", "artifacts", "pass", "warn", "block", "malformedDependencies"]
LICENSE_KEYS = ["license", "artifacts", "modules", "blockedArtifacts"]
TOTAL_KEYS = [
    "inputModules",
    "validModules",
    "artifactCount",
    "pass",
    "warn",
    "block",
    "malformedDependencies",
    "conflictCount",
    "managedMismatchCount",
    "minimumVersionCount",
    "relocationCount",
    "snapshotCount",
    "rangeCount",
    "alignmentDriftCount",
    "criticalCveCount",
]


def hash_tree(path: Path) -> dict[str, str]:
    """Return content hashes for every fixture file."""
    return {
        str(file.relative_to(path)): hashlib.sha256(file.read_bytes()).hexdigest()
        for file in sorted(path.rglob("*"))
        if file.is_file()
    }


def hash_tree_digest(path: Path) -> str:
    """Return a stable digest for the fixture tree."""
    tree = hash_tree(path)
    payload = "\n".join(f"{name}\0{digest}" for name, digest in sorted(tree.items())).encode()
    return hashlib.sha256(payload).hexdigest()


def coordinate(dep: dict) -> str:
    """Return the effective Maven coordinate identity for a dependency."""
    group = dep.get("group", "")
    artifact = dep.get("artifact", "")
    dep_type = dep.get("type", "jar")
    classifier = dep.get("classifier", "")
    if dep_type == "jar" and not classifier:
        return f"{group}:{artifact}"
    return f"{group}:{artifact}:{dep_type}:{classifier or '_'}"


def relocated_coordinate(coord: str, policy: dict) -> str:
    """Apply policy coordinate relocation before grouping."""
    return policy.get("relocations", {}).get(coord, coord)


def resolve_property(value: str, module_properties: dict[str, str], policy_properties: dict[str, str]) -> str:
    """Resolve exact ${name} property placeholders from module then policy properties."""
    if value.startswith("${") and value.endswith("}"):
        name = value[2:-1]
        if name in module_properties:
            return module_properties[name]
        if name in policy_properties:
            return policy_properties[name]
        raise KeyError(name)
    return value


def is_range(version: str) -> bool:
    """Return whether a version is a Maven range expression."""
    return bool(version) and version[0] in "[(" and version[-1] in "])"


def split_mixed(token: str) -> list:
    """Split 1.0-RC1 style tokens into numeric and qualifier pieces."""
    pieces = []
    for part in re.findall(r"\d+|[A-Za-z]+", token):
        pieces.append(int(part) if part.isdigit() else part.lower())
    return pieces


def version_tokens(version: str) -> list:
    """Tokenize a Maven-ish version for deterministic comparison."""
    cleaned = version.strip("[]()")
    out = []
    for token in re.split(r"[._,\-]", cleaned):
        if token:
            out.extend(split_mixed(token))
    return out


def qualifier_rank(value: str) -> int:
    """Return the documented qualifier order."""
    return {
        "snapshot": 0,
        "alpha": 1,
        "a": 1,
        "beta": 2,
        "b": 2,
        "milestone": 3,
        "m": 3,
        "rc": 4,
        "cr": 4,
        "final": 5,
        "ga": 5,
        "release": 5,
        "sp": 6,
    }.get(value, 3)


def compare_piece(left, right) -> int:
    """Compare token pieces using the documented Maven-ish rules."""
    if isinstance(left, int) and isinstance(right, int):
        return (left > right) - (left < right)
    if isinstance(left, int):
        return 1
    if isinstance(right, int):
        return -1
    rank_cmp = (qualifier_rank(left) > qualifier_rank(right)) - (qualifier_rank(left) < qualifier_rank(right))
    return rank_cmp or ((left > right) - (left < right))


def compare_versions(left: str, right: str) -> int:
    """Compare versions, with concrete versions ordered before range strings."""
    left_range = is_range(left)
    right_range = is_range(right)
    if left_range != right_range:
        return (left_range > right_range) - (left_range < right_range)
    left_tokens = version_tokens(left)
    right_tokens = version_tokens(right)
    width = max(len(left_tokens), len(right_tokens))
    for index in range(width):
        left_piece = left_tokens[index] if index < len(left_tokens) else "release"
        right_piece = right_tokens[index] if index < len(right_tokens) else "release"
        cmp_value = compare_piece(left_piece, right_piece)
        if cmp_value:
            return cmp_value
    return 0


def ignored(policy: dict, dep: dict) -> bool:
    """Return whether a dependency is ignored for policy checks."""
    return dep["optional"] or dep["scope"] in policy["ignoredScopes"]


def suppressed(policy: dict, dep: dict, cve: dict) -> bool:
    """Return whether a CVE is suppressed globally or on the dependency."""
    cve_id = cve.get("id")
    return bool(cve_id) and (cve_id in policy.get("suppressedCves", []) or cve_id in dep.get("suppressedCves", []))


def audit_row(kind: str, coordinate_value: str, module: str, detail: str) -> dict[str, str]:
    """Create one audit row."""
    return {"kind": kind, "coordinate": coordinate_value, "module": module, "detail": detail}


def load_model() -> tuple[dict, list[dict]]:
    """Load fixtures and produce an independent expected report plus audit rows."""
    policy = json.loads((FIXTURES / "policy" / "dependency-policy.json").read_text())
    module_files = sorted((FIXTURES / "modules").glob("*.json"))
    by_coord: dict[str, list[dict]] = defaultdict(list)
    module_acc: dict[str, dict] = {}
    audits: list[dict[str, str]] = []
    valid_modules = 0
    malformed_dependencies = 0

    for path in module_files:
        doc = json.loads(path.read_text())
        module = doc.get("module", path.stem)
        dependencies = doc.get("dependencies")
        if dependencies is None:
            malformed_dependencies += 1
            audits.append(audit_row("malformed_dependency", "", module, "missing_field:dependencies"))
            continue
        valid_modules += 1
        module_acc.setdefault(module, {"coordinates": set(), "malformed": 0})
        sources = [
            {
                "dependencies": dependencies,
                "properties": doc.get("properties", {}),
                "management": doc.get("dependencyManagement", {}),
                "imports": doc.get("imports", []),
            }
        ]
        for profile in doc.get("profiles", []):
            if profile.get("id") not in policy.get("activeProfiles", []):
                continue
            props = {**doc.get("properties", {}), **profile.get("properties", {})}
            management = {**doc.get("dependencyManagement", {}), **profile.get("dependencyManagement", {})}
            imports = doc.get("imports", []) + profile.get("imports", [])
            sources.append(
                {
                    "dependencies": profile.get("dependencies", []),
                    "properties": props,
                    "management": management,
                    "imports": imports,
                }
            )
        for source in sources:
            for raw in source["dependencies"]:
                original_coord = coordinate(raw)
                coord = relocated_coordinate(original_coord, policy)
                missing = next((field for field in ["group", "artifact", "scope", "license", "cves"] if field not in raw), None)
                if missing is not None:
                    malformed_dependencies += 1
                    module_acc[module]["malformed"] += 1
                    audits.append(audit_row("malformed_dependency", coord, module, f"missing_field:{missing}"))
                    continue
                bom_version = next(
                    (
                        policy.get("boms", {}).get(name, {}).get(candidate)
                        for name in source["imports"]
                        for candidate in [coord, original_coord]
                        if candidate in policy.get("boms", {}).get(name, {})
                    ),
                    None,
                )
                version_source = raw.get("version") or source["management"].get(coord) or source["management"].get(original_coord) or bom_version or policy.get("managedVersions", {}).get(coord)
                if version_source is None:
                    malformed_dependencies += 1
                    module_acc[module]["malformed"] += 1
                    audits.append(audit_row("malformed_dependency", coord, module, "missing_field:version"))
                    continue
                try:
                    version = resolve_property(version_source, source["properties"], policy.get("properties", {}))
                except KeyError as err:
                    malformed_dependencies += 1
                    module_acc[module]["malformed"] += 1
                    audits.append(audit_row("malformed_dependency", coord, module, f"unresolved_property:{err.args[0]}"))
                    continue
                dep = {
                    "module": module,
                    "coordinate": coord,
                    "originalCoordinate": original_coord,
                    "version": version,
                    "scope": raw["scope"],
                    "license": policy.get("licenseAliases", {}).get(raw["license"], raw["license"]),
                    "cves": raw["cves"],
                    "optional": raw.get("optional", False),
                    "suppressedCves": raw.get("suppressedCves", []),
                }
                by_coord[coord].append(dep)
                module_acc[module]["coordinates"].add(coord)

    artifacts = []
    for coord in sorted(by_coord):
        deps = by_coord[coord]
        modules = sorted({dep["module"] for dep in deps})
        versions = sorted({dep["version"] for dep in deps}, key=cmp_to_key(compare_versions))
        concrete_versions = [version for version in versions if not is_range(version)]
        selected_version = (concrete_versions or versions)[-1]
        scopes = sorted({f"{dep['scope']}:optional" if dep["optional"] else dep["scope"] for dep in deps})
        highest_cvss = 0.0
        for dep in deps:
            if ignored(policy, dep):
                continue
            for cve in dep["cves"]:
                if not suppressed(policy, dep, cve):
                    highest_cvss = max(highest_cvss, cve["cvss"])

        reasons = []
        if len(versions) > 1:
            reasons.append("version_conflict")
            audits.append(audit_row("version_conflict", coord, "*", "|".join(versions)))
        managed_source = policy.get("managedVersions", {}).get(coord)
        if managed_source:
            managed = resolve_property(managed_source, {}, policy.get("properties", {}))
            mismatches = sorted(
                {
                    dep["version"]
                    for dep in deps
                    if not ignored(policy, dep) and not is_range(dep["version"]) and dep["version"] != managed
                },
                key=cmp_to_key(compare_versions),
            )
            if mismatches:
                reasons.append("managed_version_mismatch")
                audits.append(audit_row("managed_version_mismatch", coord, "*", f"expected={managed} actual={'|'.join(mismatches)}"))
        minimum_source = policy.get("minimumVersions", {}).get(coord)
        if minimum_source:
            minimum = resolve_property(minimum_source, {}, policy.get("properties", {}))
            below = sorted(
                {
                    dep["version"]
                    for dep in deps
                    if not ignored(policy, dep) and not is_range(dep["version"]) and compare_versions(dep["version"], minimum) < 0
                },
                key=cmp_to_key(compare_versions),
            )
            if below:
                reasons.append("below_minimum_version")
                audits.append(audit_row("below_minimum_version", coord, "*", f"minimum={minimum} actual={'|'.join(below)}"))
        relocated_from = sorted({dep["originalCoordinate"] for dep in deps if dep["originalCoordinate"] != coord})
        if relocated_from:
            reasons.append("relocation_notice")
            audits.append(audit_row("relocation_notice", coord, "*", f"from={'|'.join(relocated_from)}"))
        if any(not ignored(policy, dep) and dep["license"] in policy["bannedLicenses"] for dep in deps):
            reasons.append("banned_license")
            audits.append(audit_row("banned_license", coord, "*", "policy_violation"))
        if any(
            not ignored(policy, dep)
            and any(not suppressed(policy, dep, cve) and cve["cvss"] >= policy["criticalCvss"] for cve in dep["cves"])
            for dep in deps
        ):
            reasons.append("critical_cve")
            audits.append(audit_row("critical_cve", coord, "*", f"maxCvss={highest_cvss:.1f}"))
        snapshots = sorted(
            {dep["version"] for dep in deps if not ignored(policy, dep) and "SNAPSHOT" in dep["version"].upper()},
            key=cmp_to_key(compare_versions),
        )
        if snapshots:
            reasons.append("snapshot_version")
            audits.append(audit_row("snapshot_version", coord, "*", "|".join(snapshots)))
        ranges = sorted({dep["version"] for dep in deps if not ignored(policy, dep) and is_range(dep["version"])}, key=cmp_to_key(compare_versions))
        if ranges:
            reasons.append("range_unpinned")
            audits.append(audit_row("range_unpinned", coord, "*", "|".join(ranges)))

        assert reasons == [reason for reason in REASON_ORDER if reason in reasons]
        status = "block" if any(reason in BLOCK_REASONS for reason in reasons) else ("warn" if reasons else "pass")
        artifacts.append(
            {
                "coordinate": coord,
                "selectedVersion": selected_version,
                "status": status,
                "modules": modules,
                "versions": versions,
                "reasons": reasons,
                "effectiveScopes": scopes,
                "highestCvss": round(highest_cvss, 1),
            }
        )

    artifact_by_coord = {artifact["coordinate"]: artifact for artifact in artifacts}
    for group, coords in policy.get("alignmentGroups", {}).items():
        present = [(coord, artifact_by_coord[coord]["selectedVersion"]) for coord in coords if coord in artifact_by_coord]
        if len(present) < 2:
            continue
        expected = sorted((version for _, version in present), key=cmp_to_key(compare_versions))[-1]
        for coord, version in present:
            if version == expected:
                continue
            artifact = artifact_by_coord[coord]
            if "alignment_drift" not in artifact["reasons"]:
                artifact["reasons"].append("alignment_drift")
                artifact["reasons"] = [reason for reason in REASON_ORDER if reason in artifact["reasons"]]
                artifact["status"] = "block" if any(reason in BLOCK_REASONS for reason in artifact["reasons"]) else "warn"
                audits.append(audit_row("alignment_drift", coord, "*", f"group={group} expected={expected}"))

    for artifact in artifacts:
        audits.append(audit_row("artifact_status", artifact["coordinate"], "*", f"{artifact['status']}:{'ok' if not artifact['reasons'] else '+'.join(artifact['reasons'])}"))

    status_by_coord = {artifact["coordinate"]: artifact["status"] for artifact in artifacts}
    module_summary = []
    for module in sorted(module_acc):
        coords = module_acc[module]["coordinates"]
        module_summary.append(
            {
                "module": module,
                "artifacts": len(coords),
                "pass": sum(status_by_coord[coord] == "pass" for coord in coords),
                "warn": sum(status_by_coord[coord] == "warn" for coord in coords),
                "block": sum(status_by_coord[coord] == "block" for coord in coords),
                "malformedDependencies": module_acc[module]["malformed"],
            }
        )

    license_acc: dict[str, dict] = defaultdict(lambda: {"coordinates": set(), "modules": set()})
    for coord, deps in by_coord.items():
        for dep in deps:
            license_acc[dep["license"]]["coordinates"].add(coord)
            license_acc[dep["license"]]["modules"].add(dep["module"])
    license_summary = []
    for license_name in sorted(license_acc):
        coords = license_acc[license_name]["coordinates"]
        license_summary.append(
            {
                "license": license_name,
                "artifacts": len(coords),
                "modules": len(license_acc[license_name]["modules"]),
                "blockedArtifacts": sum(status_by_coord[coord] == "block" for coord in coords),
            }
        )

    for row in module_summary:
        audits.append(
            audit_row(
                "module_summary",
                "",
                row["module"],
                f"artifacts={row['artifacts']} pass={row['pass']} warn={row['warn']} block={row['block']} malformed={row['malformedDependencies']}",
            )
        )
    for row in license_summary:
        audits.append(audit_row("license_summary", row["license"], "*", f"artifacts={row['artifacts']} modules={row['modules']} blocked={row['blockedArtifacts']}"))

    totals = {
        "inputModules": len(module_files),
        "validModules": valid_modules,
        "artifactCount": len(artifacts),
        "pass": sum(artifact["status"] == "pass" for artifact in artifacts),
        "warn": sum(artifact["status"] == "warn" for artifact in artifacts),
        "block": sum(artifact["status"] == "block" for artifact in artifacts),
        "malformedDependencies": malformed_dependencies,
        "conflictCount": sum("version_conflict" in artifact["reasons"] for artifact in artifacts),
        "managedMismatchCount": sum("managed_version_mismatch" in artifact["reasons"] for artifact in artifacts),
        "minimumVersionCount": sum("below_minimum_version" in artifact["reasons"] for artifact in artifacts),
        "relocationCount": sum("relocation_notice" in artifact["reasons"] for artifact in artifacts),
        "snapshotCount": sum("snapshot_version" in artifact["reasons"] for artifact in artifacts),
        "rangeCount": sum("range_unpinned" in artifact["reasons"] for artifact in artifacts),
        "alignmentDriftCount": sum("alignment_drift" in artifact["reasons"] for artifact in artifacts),
        "criticalCveCount": sum("critical_cve" in artifact["reasons"] for artifact in artifacts),
    }
    return {"artifacts": artifacts, "moduleSummary": module_summary, "licenseSummary": license_summary, "totals": totals}, audits


def expected_csv(audits: list[dict[str, str]]) -> str:
    """Return the expected CSV text from audit rows."""
    rows = sorted(audits, key=lambda row: tuple(row.values()))
    return "\n".join(["kind,coordinate,module,detail"] + [",".join(csv_escape(row[field]) for field in ["kind", "coordinate", "module", "detail"]) for row in rows])


def csv_escape(value: str) -> str:
    """Escape CSV fields containing commas, quotes, or newlines."""
    if any(char in value for char in [",", '"', "\n", "\r"]):
        return '"' + value.replace('"', '""') + '"'
    return value


def run_cli() -> dict[str, dict[str, str]]:
    """Run the Rust CLI once and return fixture hashes before and after."""
    assert hash_tree_digest(FIXTURES) == EXPECTED_FIXTURE_TREE_SHA256
    before = hash_tree(FIXTURES)
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["cargo", "run", "--quiet", "--locked", "--", "--fixtures", str(FIXTURES), "--out", str(OUT)],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    after = hash_tree(FIXTURES)
    assert before == after
    assert hash_tree_digest(FIXTURES) == EXPECTED_FIXTURE_TREE_SHA256
    return {"before": before, "after": after}


def test_outputs_exist_and_only_documented_outputs():
    """The command writes exactly the documented JSON and CSV outputs."""
    run_cli()
    assert JSON_OUT.exists()
    assert CSV_OUT.exists()
    assert sorted(p.name for p in OUT.iterdir()) == ["dependency-audit.csv", "dependency-convergence.json"]


def test_json_schema_key_order_and_totals():
    """The JSON report uses the documented key order and exact totals."""
    run_cli()
    data = json.loads(JSON_OUT.read_text(), object_pairs_hook=OrderedDict)
    expected, _ = load_model()
    assert list(data.keys()) == ["artifacts", "moduleSummary", "licenseSummary", "totals"]
    assert [list(item.keys()) for item in data["artifacts"]] == [ARTIFACT_KEYS] * len(expected["artifacts"])
    assert [list(item.keys()) for item in data["moduleSummary"]] == [MODULE_KEYS] * len(expected["moduleSummary"])
    assert [list(item.keys()) for item in data["licenseSummary"]] == [LICENSE_KEYS] * len(expected["licenseSummary"])
    assert list(data["totals"].keys()) == TOTAL_KEYS
    assert data["totals"] == expected["totals"]


def test_json_report_matches_policy_model():
    """Every computed JSON row matches the independent policy model."""
    run_cli()
    expected, _ = load_model()
    assert json.loads(JSON_OUT.read_text()) == expected


def test_audit_csv_sorting_line_endings_and_contents():
    """Audit CSV has exact rows, LF endings, no trailing newline, and documented sorting."""
    run_cli()
    _, audits = load_model()
    raw = CSV_OUT.read_bytes()
    assert b"\r" not in raw
    assert not raw.endswith(b"\n")
    text = raw.decode()
    assert text == expected_csv(audits)
    rows = list(csv.DictReader(text.splitlines()))
    assert rows == sorted(rows, key=lambda row: tuple(row.values()))


def test_fixture_immutability_and_pretty_json():
    """Running the CLI leaves fixtures unchanged and writes stable pretty JSON."""
    hashes = run_cli()
    assert hashes["before"] == hashes["after"]
    raw = JSON_OUT.read_text()
    assert raw.endswith("\n")
    assert not raw.endswith("\n\n")
    assert '\n  "artifacts": [' in raw


def test_dependency_management_type_classifier_and_qualifiers():
    """Managed versions, property placeholders, non-default coordinates, and Maven qualifiers are enforced."""
    run_cli()
    artifacts = {item["coordinate"]: item for item in json.loads(JSON_OUT.read_text())["artifacts"]}
    assert artifacts["com.acme:shared-model"]["selectedVersion"] == "1.4.0"
    assert artifacts["com.acme:shared-model"]["reasons"] == ["version_conflict", "managed_version_mismatch"]
    assert artifacts["com.acme:tooling:jar:linux-x86_64"]["reasons"] == ["managed_version_mismatch", "snapshot_version"]
    assert artifacts["com.google.guava:guava"]["selectedVersion"] == "32.1.3-jre"
    assert artifacts["com.google.guava:guava"]["reasons"] == ["version_conflict", "managed_version_mismatch", "below_minimum_version"]
    assert artifacts["com.profile:runtime-agent"]["reasons"] == ["managed_version_mismatch", "below_minimum_version"]
    assert "com.gnu:dev-only-helper" not in artifacts
    assert artifacts["org.springframework:spring-core"]["selectedVersion"] == "6.1.5"
    assert artifacts["org.springframework:spring-core"]["status"] == "pass"
    assert artifacts["com.bad:copyleft-helper"]["reasons"] == ["banned_license"]
    assert artifacts["com.sun.mail:jakarta.mail"]["reasons"] == ["version_conflict", "managed_version_mismatch", "below_minimum_version", "relocation_notice"]
    assert artifacts["org.jetbrains.kotlin:kotlin-stdlib"]["selectedVersion"] == "1.9.22"
    assert artifacts["org.jetbrains.kotlin:kotlin-stdlib"]["reasons"] == ["version_conflict", "managed_version_mismatch"]
    assert artifacts["net.java.dev.jna:jna-platform:so:linux-x86_64"]["status"] == "block"


def test_ignored_optional_ranges_and_cve_suppression():
    """Ignored scopes, optional dependencies, version ranges, and CVE suppressions interact correctly."""
    run_cli()
    data = json.loads(JSON_OUT.read_text())
    artifacts = {item["coordinate"]: item for item in data["artifacts"]}
    assert artifacts["org.apache.commons:commons-lang3"]["reasons"] == ["range_unpinned"]
    assert artifacts["org.apache.commons:commons-lang3"]["status"] == "warn"
    assert artifacts["commons-io:commons-io"]["highestCvss"] == 0.0
    assert "critical_cve" not in artifacts["commons-io:commons-io"]["reasons"]
    assert artifacts["com.gnu:readline"]["effectiveScopes"] == ["compile", "compile:optional", "provided"]
    assert artifacts["com.gnu:readline"]["reasons"] == ["version_conflict", "banned_license"]
    assert artifacts["org.springframework:spring-context"]["reasons"] == ["below_minimum_version"]
    assert artifacts["com.sun.activation:jakarta.activation"]["reasons"] == ["managed_version_mismatch", "below_minimum_version", "relocation_notice"]
    assert artifacts["com.fasterxml.jackson.module:jackson-module-parameter-names"]["reasons"] == ["alignment_drift"]
    assert artifacts["com.fasterxml.jackson.module:jackson-module-parameter-names"]["status"] == "warn"
    assert data["totals"]["rangeCount"] == 1
    assert data["totals"]["snapshotCount"] == 1
    assert data["totals"]["alignmentDriftCount"] == 1
    assert data["totals"]["minimumVersionCount"] == 5
    assert data["totals"]["relocationCount"] == 2


def test_summaries_and_audit_edge_rows_are_present():
    """Module/license summaries and exact audit rows cover hard edge cases."""
    run_cli()
    data = json.loads(JSON_OUT.read_text())
    modules = {item["module"]: item for item in data["moduleSummary"]}
    licenses = {item["license"]: item for item in data["licenseSummary"]}
    rows = list(csv.DictReader(CSV_OUT.read_text().splitlines()))
    details = {(row["kind"], row["coordinate"], row["module"]): row["detail"] for row in rows}
    assert modules["platform"] == {"module": "platform", "artifacts": 4, "pass": 1, "warn": 1, "block": 2, "malformedDependencies": 0}
    assert modules["property-service"] == {"module": "property-service", "artifacts": 2, "pass": 0, "warn": 0, "block": 2, "malformedDependencies": 1}
    assert modules["spring-web"] == {"module": "spring-web", "artifacts": 2, "pass": 1, "warn": 0, "block": 1, "malformedDependencies": 0}
    assert modules["profiled-runtime"] == {"module": "profiled-runtime", "artifacts": 2, "pass": 1, "warn": 0, "block": 1, "malformedDependencies": 0}
    assert modules["legacy-relocation"] == {"module": "legacy-relocation", "artifacts": 2, "pass": 0, "warn": 0, "block": 2, "malformedDependencies": 0}
    assert modules["broken-dep"]["malformedDependencies"] == 1
    assert licenses["GPL-3.0"]["blockedArtifacts"] == 2
    assert "Apache License 2.0" not in licenses
    assert details[("managed_version_mismatch", "com.acme:shared-model", "*")] == "expected=1.4.0 actual=1.3.0"
    assert details[("managed_version_mismatch", "com.fasterxml.jackson.core:jackson-databind", "*")] == "expected=2.15.2 actual=2.12.0|2.14.3"
    assert details[("below_minimum_version", "com.google.guava:guava", "*")] == "minimum=32.1.3-jre actual=31.1-jre"
    assert details[("below_minimum_version", "com.profile:runtime-agent", "*")] == "minimum=5.0.0 actual=4.9.0"
    assert details[("below_minimum_version", "org.springframework:spring-context", "*")] == "minimum=6.1.5 actual=6.0.0"
    assert details[("relocation_notice", "com.sun.mail:jakarta.mail", "*")] == "from=javax.mail:mail"
    assert details[("relocation_notice", "com.sun.activation:jakarta.activation", "*")] == "from=javax.activation:activation"
    assert details[("alignment_drift", "com.fasterxml.jackson.module:jackson-module-parameter-names", "*")] == "group=jackson expected=2.15.2"
    assert details[("range_unpinned", "org.apache.commons:commons-lang3", "*")] == "[3.8,4.0)"
    assert details[("snapshot_version", "com.acme:tooling:jar:linux-x86_64", "*")] == "2.0.0-SNAPSHOT"
    assert details[("critical_cve", "net.java.dev.jna:jna-platform:so:linux-x86_64", "*")] == "maxCvss=9.9"
    assert details[("module_summary", "", "platform")] == "artifacts=4 pass=1 warn=1 block=2 malformed=0"
    assert details[("malformed_dependency", "com.bad:unresolved-property", "property-service")] == "unresolved_property:missing.version"
    assert details[("malformed_dependency", "com.bad:missing-version", "broken-dep")] == "missing_field:version"
