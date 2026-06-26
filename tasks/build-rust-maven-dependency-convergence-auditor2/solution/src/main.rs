use serde::{Deserialize, Serialize};
use std::cmp::Ordering;
use std::collections::{BTreeMap, BTreeSet};
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Deserialize)]
struct Policy {
    #[serde(rename = "bannedLicenses")]
    banned_licenses: Vec<String>,
    #[serde(rename = "criticalCvss")]
    critical_cvss: f64,
    #[serde(rename = "ignoredScopes")]
    ignored_scopes: Vec<String>,
    #[serde(rename = "activeProfiles", default)]
    active_profiles: Vec<String>,
    #[serde(rename = "suppressedCves", default)]
    suppressed_cves: Vec<String>,
    #[serde(rename = "licenseAliases", default)]
    license_aliases: BTreeMap<String, String>,
    #[serde(rename = "managedVersions", default)]
    managed_versions: BTreeMap<String, String>,
    #[serde(rename = "minimumVersions", default)]
    minimum_versions: BTreeMap<String, String>,
    #[serde(default)]
    relocations: BTreeMap<String, String>,
    #[serde(default)]
    boms: BTreeMap<String, BTreeMap<String, String>>,
    #[serde(default)]
    properties: BTreeMap<String, String>,
    #[serde(rename = "alignmentGroups", default)]
    alignment_groups: BTreeMap<String, Vec<String>>,
}

#[derive(Deserialize)]
struct ModuleDoc {
    module: Option<String>,
    #[serde(default)]
    properties: BTreeMap<String, String>,
    #[serde(default)]
    imports: Vec<String>,
    #[serde(rename = "dependencyManagement", default)]
    dependency_management: BTreeMap<String, String>,
    dependencies: Option<Vec<RawDependency>>,
    #[serde(default)]
    profiles: Vec<ProfileDoc>,
}

#[derive(Clone, Deserialize)]
struct ProfileDoc {
    id: String,
    #[serde(default)]
    properties: BTreeMap<String, String>,
    #[serde(default)]
    imports: Vec<String>,
    #[serde(rename = "dependencyManagement", default)]
    dependency_management: BTreeMap<String, String>,
    #[serde(default)]
    dependencies: Vec<RawDependency>,
}

#[derive(Clone, Deserialize)]
struct RawDependency {
    group: Option<String>,
    artifact: Option<String>,
    version: Option<String>,
    scope: Option<String>,
    license: Option<String>,
    cves: Option<Vec<Cve>>,
    #[serde(rename = "type")]
    dep_type: Option<String>,
    classifier: Option<String>,
    #[serde(default)]
    optional: bool,
    #[serde(rename = "suppressedCves", default)]
    suppressed_cves: Vec<String>,
}

#[derive(Clone, Deserialize)]
struct Cve {
    id: Option<String>,
    cvss: f64,
}

#[derive(Clone)]
struct Dependency {
    module: String,
    original_coordinate: String,
    version: String,
    scope: String,
    license: String,
    cves: Vec<Cve>,
    optional: bool,
    suppressed_cves: Vec<String>,
}

struct DependencySource {
    dependencies: Vec<RawDependency>,
    properties: BTreeMap<String, String>,
    dependency_management: BTreeMap<String, String>,
    imports: Vec<String>,
}

#[derive(Serialize)]
struct Report {
    artifacts: Vec<ArtifactRow>,
    #[serde(rename = "moduleSummary")]
    module_summary: Vec<ModuleSummaryRow>,
    #[serde(rename = "licenseSummary")]
    license_summary: Vec<LicenseSummaryRow>,
    totals: Totals,
}

#[derive(Clone, Serialize)]
struct ArtifactRow {
    coordinate: String,
    #[serde(rename = "selectedVersion")]
    selected_version: String,
    status: String,
    modules: Vec<String>,
    versions: Vec<String>,
    reasons: Vec<String>,
    #[serde(rename = "effectiveScopes")]
    effective_scopes: Vec<String>,
    #[serde(rename = "highestCvss")]
    highest_cvss: f64,
}

#[derive(Serialize)]
struct ModuleSummaryRow {
    module: String,
    artifacts: usize,
    pass: usize,
    warn: usize,
    block: usize,
    #[serde(rename = "malformedDependencies")]
    malformed_dependencies: usize,
}

#[derive(Serialize)]
struct LicenseSummaryRow {
    license: String,
    artifacts: usize,
    modules: usize,
    #[serde(rename = "blockedArtifacts")]
    blocked_artifacts: usize,
}

#[derive(Serialize)]
struct Totals {
    #[serde(rename = "inputModules")]
    input_modules: usize,
    #[serde(rename = "validModules")]
    valid_modules: usize,
    #[serde(rename = "artifactCount")]
    artifact_count: usize,
    pass: usize,
    warn: usize,
    block: usize,
    #[serde(rename = "malformedDependencies")]
    malformed_dependencies: usize,
    #[serde(rename = "conflictCount")]
    conflict_count: usize,
    #[serde(rename = "managedMismatchCount")]
    managed_mismatch_count: usize,
    #[serde(rename = "minimumVersionCount")]
    minimum_version_count: usize,
    #[serde(rename = "relocationCount")]
    relocation_count: usize,
    #[serde(rename = "snapshotCount")]
    snapshot_count: usize,
    #[serde(rename = "rangeCount")]
    range_count: usize,
    #[serde(rename = "alignmentDriftCount")]
    alignment_drift_count: usize,
    #[serde(rename = "criticalCveCount")]
    critical_cve_count: usize,
}

#[derive(Default)]
struct ModuleAccumulator {
    coordinates: BTreeSet<String>,
    malformed_dependencies: usize,
}

#[derive(Default)]
struct LicenseAccumulator {
    coordinates: BTreeSet<String>,
    modules: BTreeSet<String>,
}

#[derive(Eq, PartialEq, Ord, PartialOrd)]
struct AuditRow {
    kind: String,
    coordinate: String,
    module: String,
    detail: String,
}

fn main() {
    if let Err(err) = run() {
        eprintln!("{err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let (fixtures, out) = parse_args()?;
    fs::create_dir_all(&out).map_err(|e| e.to_string())?;
    let policy: Policy = read_json(&fixtures.join("policy").join("dependency-policy.json"))?;
    let files = json_files(&fixtures.join("modules"))?;

    let mut valid_modules = 0usize;
    let mut malformed_dependencies = 0usize;
    let mut by_coord: BTreeMap<String, Vec<Dependency>> = BTreeMap::new();
    let mut module_acc: BTreeMap<String, ModuleAccumulator> = BTreeMap::new();
    let mut audit = BTreeSet::new();

    for path in &files {
        let module_doc: ModuleDoc = read_json(path)?;
        let module = module_doc
            .module
            .clone()
            .unwrap_or_else(|| path.file_stem().and_then(|s| s.to_str()).unwrap_or("unknown").to_string());
        let Some(dependencies) = module_doc.dependencies else {
            malformed_dependencies += 1;
            audit.insert(AuditRow {
                kind: "malformed_dependency".to_string(),
                coordinate: String::new(),
                module,
                detail: "missing_field:dependencies".to_string(),
            });
            continue;
        };

        valid_modules += 1;
        module_acc.entry(module.clone()).or_default();
        let mut sources = Vec::new();
        sources.push(DependencySource {
            dependencies,
            properties: module_doc.properties.clone(),
            dependency_management: module_doc.dependency_management.clone(),
            imports: module_doc.imports.clone(),
        });
        for profile in &module_doc.profiles {
            if !policy.active_profiles.iter().any(|active| active == &profile.id) {
                continue;
            }
            let mut properties = module_doc.properties.clone();
            properties.extend(profile.properties.clone());
            let mut dependency_management = module_doc.dependency_management.clone();
            dependency_management.extend(profile.dependency_management.clone());
            let mut imports = module_doc.imports.clone();
            imports.extend(profile.imports.clone());
            sources.push(DependencySource {
                dependencies: profile.dependencies.clone(),
                properties,
                dependency_management,
                imports,
            });
        }
        for source in sources {
            for raw in source.dependencies {
                let original_coordinate = coordinate_from_raw(&raw);
                let coordinate = relocated_coordinate(&original_coordinate, &policy);
                if let Some(field) = missing_field(&raw) {
                    malformed_dependencies += 1;
                    module_acc.entry(module.clone()).or_default().malformed_dependencies += 1;
                    audit.insert(AuditRow {
                        kind: "malformed_dependency".to_string(),
                        coordinate,
                        module: module.clone(),
                        detail: format!("missing_field:{field}"),
                    });
                    continue;
                }
                let version_source = raw
                    .version
                    .as_deref()
                    .or_else(|| source.dependency_management.get(&coordinate).map(|value| value.as_str()))
                    .or_else(|| source.dependency_management.get(&original_coordinate).map(|value| value.as_str()))
                    .or_else(|| bom_version(&source.imports, &coordinate, &policy).map(|value| value.as_str()))
                    .or_else(|| bom_version(&source.imports, &original_coordinate, &policy).map(|value| value.as_str()))
                    .or_else(|| policy.managed_versions.get(&coordinate).map(|value| value.as_str()));
                let Some(version_source) = version_source else {
                    malformed_dependencies += 1;
                    module_acc.entry(module.clone()).or_default().malformed_dependencies += 1;
                    audit.insert(AuditRow {
                        kind: "malformed_dependency".to_string(),
                        coordinate,
                        module: module.clone(),
                        detail: "missing_field:version".to_string(),
                    });
                    continue;
                };
                let version = match resolve_properties(version_source, &source.properties, &policy.properties) {
                    Ok(value) => value,
                    Err(name) => {
                        malformed_dependencies += 1;
                        module_acc.entry(module.clone()).or_default().malformed_dependencies += 1;
                        audit.insert(AuditRow {
                            kind: "malformed_dependency".to_string(),
                            coordinate,
                            module: module.clone(),
                            detail: format!("unresolved_property:{name}"),
                        });
                        continue;
                    }
                };

                let dep = Dependency {
                    module: module.clone(),
                    original_coordinate,
                    version,
                    scope: raw.scope.unwrap(),
                    license: canonical_license(&raw.license.unwrap(), &policy),
                    cves: raw.cves.unwrap(),
                    optional: raw.optional,
                    suppressed_cves: raw.suppressed_cves,
                };
                module_acc.entry(module.clone()).or_default().coordinates.insert(coordinate.clone());
                by_coord.entry(coordinate).or_default().push(dep);
            }
        }
    }

    let mut artifacts = Vec::new();
    for (coordinate, deps) in &by_coord {
        artifacts.push(evaluate_artifact(coordinate, deps, &policy, &mut audit));
    }
    apply_alignment(&mut artifacts, &policy, &mut audit);
    for row in &artifacts {
        audit.insert(AuditRow {
            kind: "artifact_status".to_string(),
            coordinate: row.coordinate.clone(),
            module: "*".to_string(),
            detail: format!("{}:{}", row.status, if row.reasons.is_empty() { "ok".to_string() } else { row.reasons.join("+") }),
        });
    }

    let artifact_status: BTreeMap<String, String> = artifacts
        .iter()
        .map(|row| (row.coordinate.clone(), row.status.clone()))
        .collect();
    let module_summary = build_module_summary(module_acc, &artifact_status);
    let license_summary = build_license_summary(&by_coord, &artifact_status);

    for row in &module_summary {
        audit.insert(AuditRow {
            kind: "module_summary".to_string(),
            coordinate: String::new(),
            module: row.module.clone(),
            detail: format!(
                "artifacts={} pass={} warn={} block={} malformed={}",
                row.artifacts, row.pass, row.warn, row.block, row.malformed_dependencies
            ),
        });
    }
    for row in &license_summary {
        audit.insert(AuditRow {
            kind: "license_summary".to_string(),
            coordinate: row.license.clone(),
            module: "*".to_string(),
            detail: format!("artifacts={} modules={} blocked={}", row.artifacts, row.modules, row.blocked_artifacts),
        });
    }

    let totals = Totals {
        input_modules: files.len(),
        valid_modules,
        artifact_count: artifacts.len(),
        pass: artifacts.iter().filter(|row| row.status == "pass").count(),
        warn: artifacts.iter().filter(|row| row.status == "warn").count(),
        block: artifacts.iter().filter(|row| row.status == "block").count(),
        malformed_dependencies,
        conflict_count: artifacts.iter().filter(|row| has_reason(row, "version_conflict")).count(),
        managed_mismatch_count: artifacts.iter().filter(|row| has_reason(row, "managed_version_mismatch")).count(),
        minimum_version_count: artifacts.iter().filter(|row| has_reason(row, "below_minimum_version")).count(),
        relocation_count: artifacts.iter().filter(|row| has_reason(row, "relocation_notice")).count(),
        snapshot_count: artifacts.iter().filter(|row| has_reason(row, "snapshot_version")).count(),
        range_count: artifacts.iter().filter(|row| has_reason(row, "range_unpinned")).count(),
        alignment_drift_count: artifacts.iter().filter(|row| has_reason(row, "alignment_drift")).count(),
        critical_cve_count: artifacts.iter().filter(|row| has_reason(row, "critical_cve")).count(),
    };

    let report = Report {
        artifacts,
        module_summary,
        license_summary,
        totals,
    };
    let json = serde_json::to_string_pretty(&report).map_err(|e| e.to_string())?;
    fs::write(out.join("dependency-convergence.json"), format!("{json}\n")).map_err(|e| e.to_string())?;
    fs::write(out.join("dependency-audit.csv"), render_audit(&audit)).map_err(|e| e.to_string())?;
    Ok(())
}

fn evaluate_artifact(coordinate: &str, deps: &[Dependency], policy: &Policy, audit: &mut BTreeSet<AuditRow>) -> ArtifactRow {
    let mut modules = BTreeSet::new();
    let mut versions = BTreeSet::new();
    let mut scopes = BTreeSet::new();
    let mut highest_cvss = 0.0f64;
    let mut reasons = Vec::new();

    for dep in deps {
        modules.insert(dep.module.clone());
        versions.insert(dep.version.clone());
        scopes.insert(if dep.optional { format!("{}:optional", dep.scope) } else { dep.scope.clone() });
        if ignored(policy, dep) {
            continue;
        }
        for cve in &dep.cves {
            if !suppressed(policy, dep, cve) {
                highest_cvss = highest_cvss.max(cve.cvss);
            }
        }
    }

    let mut version_list: Vec<String> = versions.into_iter().collect();
    version_list.sort_by(|a, b| compare_versions(a, b));
    let concrete_versions: Vec<String> = version_list.iter().filter(|version| !is_range(version)).cloned().collect();
    let selected_version = concrete_versions.last().cloned().or_else(|| version_list.last().cloned()).unwrap_or_default();

    if version_list.len() > 1 {
        reasons.push("version_conflict".to_string());
        audit.insert(AuditRow {
            kind: "version_conflict".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: version_list.join("|"),
        });
    }

    if let Some(managed_raw) = policy.managed_versions.get(coordinate) {
        let managed = resolve_properties(managed_raw, &BTreeMap::new(), &policy.properties).unwrap_or_else(|_| managed_raw.clone());
        let mismatches: Vec<String> = deps
            .iter()
            .filter(|dep| !ignored(policy, dep))
            .filter(|dep| !is_range(&dep.version))
            .filter(|dep| dep.version != managed)
            .map(|dep| dep.version.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        if !mismatches.is_empty() {
            reasons.push("managed_version_mismatch".to_string());
            audit.insert(AuditRow {
                kind: "managed_version_mismatch".to_string(),
                coordinate: coordinate.to_string(),
                module: "*".to_string(),
                detail: format!("expected={} actual={}", managed, mismatches.join("|")),
            });
        }
    }

    if let Some(minimum_raw) = policy.minimum_versions.get(coordinate) {
        let minimum = resolve_properties(minimum_raw, &BTreeMap::new(), &policy.properties).unwrap_or_else(|_| minimum_raw.clone());
        let below: Vec<String> = deps
            .iter()
            .filter(|dep| !ignored(policy, dep))
            .filter(|dep| !is_range(&dep.version))
            .filter(|dep| compare_versions(&dep.version, &minimum) == Ordering::Less)
            .map(|dep| dep.version.clone())
            .collect::<BTreeSet<_>>()
            .into_iter()
            .collect();
        if !below.is_empty() {
            reasons.push("below_minimum_version".to_string());
            audit.insert(AuditRow {
                kind: "below_minimum_version".to_string(),
                coordinate: coordinate.to_string(),
                module: "*".to_string(),
                detail: format!("minimum={} actual={}", minimum, below.join("|")),
            });
        }
    }

    let relocated_from: Vec<String> = deps
        .iter()
        .filter(|dep| dep.original_coordinate != coordinate)
        .map(|dep| dep.original_coordinate.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    if !relocated_from.is_empty() {
        reasons.push("relocation_notice".to_string());
        audit.insert(AuditRow {
            kind: "relocation_notice".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: format!("from={}", relocated_from.join("|")),
        });
    }

    if deps.iter().any(|dep| !ignored(policy, dep) && policy.banned_licenses.iter().any(|license| license == &dep.license)) {
        reasons.push("banned_license".to_string());
        audit.insert(AuditRow {
            kind: "banned_license".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: "policy_violation".to_string(),
        });
    }

    if deps.iter().any(|dep| {
        !ignored(policy, dep)
            && dep
                .cves
                .iter()
                .any(|cve| !suppressed(policy, dep, cve) && cve.cvss >= policy.critical_cvss)
    }) {
        reasons.push("critical_cve".to_string());
        audit.insert(AuditRow {
            kind: "critical_cve".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: format!("maxCvss={:.1}", highest_cvss),
        });
    }

    let snapshots: Vec<String> = deps
        .iter()
        .filter(|dep| !ignored(policy, dep) && dep.version.to_ascii_uppercase().contains("SNAPSHOT"))
        .map(|dep| dep.version.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    if !snapshots.is_empty() {
        reasons.push("snapshot_version".to_string());
        audit.insert(AuditRow {
            kind: "snapshot_version".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: snapshots.join("|"),
        });
    }

    let ranges: Vec<String> = deps
        .iter()
        .filter(|dep| !ignored(policy, dep) && is_range(&dep.version))
        .map(|dep| dep.version.clone())
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect();
    if !ranges.is_empty() {
        reasons.push("range_unpinned".to_string());
        audit.insert(AuditRow {
            kind: "range_unpinned".to_string(),
            coordinate: coordinate.to_string(),
            module: "*".to_string(),
            detail: ranges.join("|"),
        });
    }

    let status = status_for_reasons(&reasons);
    ArtifactRow {
        coordinate: coordinate.to_string(),
        selected_version,
        status,
        modules: modules.into_iter().collect(),
        versions: version_list,
        reasons,
        effective_scopes: scopes.into_iter().collect(),
        highest_cvss: round_one(highest_cvss),
    }
}

fn build_module_summary(
    module_acc: BTreeMap<String, ModuleAccumulator>,
    artifact_status: &BTreeMap<String, String>,
) -> Vec<ModuleSummaryRow> {
    module_acc
        .into_iter()
        .map(|(module, row)| {
            let mut pass = 0;
            let mut warn = 0;
            let mut block = 0;
            for coord in &row.coordinates {
                match artifact_status.get(coord).map(|value| value.as_str()) {
                    Some("pass") => pass += 1,
                    Some("warn") => warn += 1,
                    Some("block") => block += 1,
                    _ => {}
                }
            }
            ModuleSummaryRow {
                module,
                artifacts: row.coordinates.len(),
                pass,
                warn,
                block,
                malformed_dependencies: row.malformed_dependencies,
            }
        })
        .collect()
}

fn build_license_summary(
    by_coord: &BTreeMap<String, Vec<Dependency>>,
    artifact_status: &BTreeMap<String, String>,
) -> Vec<LicenseSummaryRow> {
    let mut acc: BTreeMap<String, LicenseAccumulator> = BTreeMap::new();
    for (coordinate, deps) in by_coord {
        for dep in deps {
            let row = acc.entry(dep.license.clone()).or_default();
            row.coordinates.insert(coordinate.clone());
            row.modules.insert(dep.module.clone());
        }
    }
    acc.into_iter()
        .map(|(license, row)| {
            let blocked_artifacts = row
                .coordinates
                .iter()
                .filter(|coord| artifact_status.get(*coord).map(|status| status == "block").unwrap_or(false))
                .count();
            LicenseSummaryRow {
                license,
                artifacts: row.coordinates.len(),
                modules: row.modules.len(),
                blocked_artifacts,
            }
        })
        .collect()
}

fn apply_alignment(artifacts: &mut [ArtifactRow], policy: &Policy, audit: &mut BTreeSet<AuditRow>) {
    let selected_by_coord: BTreeMap<String, String> = artifacts
        .iter()
        .map(|row| (row.coordinate.clone(), row.selected_version.clone()))
        .collect();
    for (group, coordinates) in &policy.alignment_groups {
        let mut present: Vec<(String, String)> = coordinates
            .iter()
            .filter_map(|coord| selected_by_coord.get(coord).map(|version| (coord.clone(), version.clone())))
            .collect();
        if present.len() < 2 {
            continue;
        }
        present.sort_by(|a, b| compare_versions(&a.1, &b.1));
        let expected = present.last().map(|(_, version)| version.clone()).unwrap_or_default();
        for (coord, version) in present {
            if version == expected {
                continue;
            }
            if let Some(row) = artifacts.iter_mut().find(|row| row.coordinate == coord) {
                if !row.reasons.iter().any(|reason| reason == "alignment_drift") {
                    row.reasons.push("alignment_drift".to_string());
                    row.reasons = ordered_reasons(&row.reasons);
                    row.status = status_for_reasons(&row.reasons);
                    audit.insert(AuditRow {
                        kind: "alignment_drift".to_string(),
                        coordinate: coord,
                        module: "*".to_string(),
                        detail: format!("group={group} expected={expected}"),
                    });
                }
            }
        }
    }
}

fn ordered_reasons(reasons: &[String]) -> Vec<String> {
    [
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
    .iter()
    .filter(|reason| reasons.iter().any(|value| value == **reason))
    .map(|reason| (*reason).to_string())
    .collect()
}

fn status_for_reasons(reasons: &[String]) -> String {
    if reasons
        .iter()
        .any(|reason| matches!(reason.as_str(), "managed_version_mismatch" | "below_minimum_version" | "banned_license" | "critical_cve"))
    {
        "block"
    } else if reasons.is_empty() {
        "pass"
    } else {
        "warn"
    }
    .to_string()
}

fn parse_args() -> Result<(PathBuf, PathBuf), String> {
    let mut fixtures = PathBuf::from("/app/fixtures");
    let mut out = PathBuf::from("/app/out");
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--fixtures" => fixtures = PathBuf::from(args.next().ok_or("missing --fixtures value")?),
            "--out" => out = PathBuf::from(args.next().ok_or("missing --out value")?),
            other => return Err(format!("unknown argument {other}")),
        }
    }
    Ok((fixtures, out))
}

fn coordinate_from_raw(dep: &RawDependency) -> String {
    let group = dep.group.clone().unwrap_or_default();
    let artifact = dep.artifact.clone().unwrap_or_default();
    let dep_type = dep.dep_type.clone().unwrap_or_else(|| "jar".to_string());
    let classifier = dep.classifier.clone().unwrap_or_default();
    if dep_type == "jar" && classifier.is_empty() {
        format!("{group}:{artifact}")
    } else {
        format!("{group}:{artifact}:{dep_type}:{}", if classifier.is_empty() { "_" } else { &classifier })
    }
}

fn relocated_coordinate(coordinate: &str, policy: &Policy) -> String {
    policy.relocations.get(coordinate).cloned().unwrap_or_else(|| coordinate.to_string())
}

fn bom_version<'a>(imports: &[String], coordinate: &str, policy: &'a Policy) -> Option<&'a String> {
    imports
        .iter()
        .filter_map(|name| policy.boms.get(name))
        .find_map(|bom| bom.get(coordinate))
}

fn canonical_license(license: &str, policy: &Policy) -> String {
    policy.license_aliases.get(license).cloned().unwrap_or_else(|| license.to_string())
}

fn missing_field(dep: &RawDependency) -> Option<&'static str> {
    if dep.group.is_none() {
        Some("group")
    } else if dep.artifact.is_none() {
        Some("artifact")
    } else if dep.scope.is_none() {
        Some("scope")
    } else if dep.license.is_none() {
        Some("license")
    } else if dep.cves.is_none() {
        Some("cves")
    } else {
        None
    }
}

fn resolve_properties(
    value: &str,
    module_properties: &BTreeMap<String, String>,
    policy_properties: &BTreeMap<String, String>,
) -> Result<String, String> {
    let Some(name) = value.strip_prefix("${").and_then(|rest| rest.strip_suffix('}')) else {
        return Ok(value.to_string());
    };
    module_properties
        .get(name)
        .or_else(|| policy_properties.get(name))
        .cloned()
        .ok_or_else(|| name.to_string())
}

fn ignored(policy: &Policy, dep: &Dependency) -> bool {
    dep.optional || policy.ignored_scopes.iter().any(|item| item == &dep.scope)
}

fn suppressed(policy: &Policy, dep: &Dependency, cve: &Cve) -> bool {
    let Some(id) = &cve.id else {
        return false;
    };
    policy.suppressed_cves.iter().any(|item| item == id) || dep.suppressed_cves.iter().any(|item| item == id)
}

fn is_range(version: &str) -> bool {
    (version.starts_with('[') || version.starts_with('(')) && (version.ends_with(']') || version.ends_with(')'))
}

fn has_reason(row: &ArtifactRow, reason: &str) -> bool {
    row.reasons.iter().any(|item| item == reason)
}

fn compare_versions(a: &str, b: &str) -> Ordering {
    let ar = is_range(a);
    let br = is_range(b);
    if ar != br {
        return ar.cmp(&br);
    }
    let left = tokenize_version(a);
    let right = tokenize_version(b);
    for index in 0..left.len().max(right.len()) {
        let av = left.get(index).cloned().unwrap_or(Token::Qualifier("release".to_string()));
        let bv = right.get(index).cloned().unwrap_or(Token::Qualifier("release".to_string()));
        let ordering = compare_token(&av, &bv);
        if ordering != Ordering::Equal {
            return ordering;
        }
    }
    Ordering::Equal
}

#[derive(Clone, Debug)]
enum Token {
    Number(i64),
    Qualifier(String),
}

fn tokenize_version(version: &str) -> Vec<Token> {
    version
        .trim_matches(|ch| matches!(ch, '[' | ']' | '(' | ')'))
        .split(|ch| matches!(ch, '.' | '-' | '_' | ','))
        .filter(|part| !part.is_empty())
        .flat_map(split_mixed_token)
        .collect()
}

fn split_mixed_token(part: &str) -> Vec<Token> {
    let mut out = Vec::new();
    let mut current = String::new();
    let mut digit_mode: Option<bool> = None;
    for ch in part.chars() {
        let is_digit = ch.is_ascii_digit();
        if digit_mode == Some(is_digit) || digit_mode.is_none() {
            current.push(ch);
            digit_mode = Some(is_digit);
        } else {
            push_version_token(&mut out, &current, digit_mode.unwrap_or(false));
            current.clear();
            current.push(ch);
            digit_mode = Some(is_digit);
        }
    }
    if !current.is_empty() {
        push_version_token(&mut out, &current, digit_mode.unwrap_or(false));
    }
    out
}

fn push_version_token(out: &mut Vec<Token>, value: &str, is_digit: bool) {
    if is_digit {
        out.push(Token::Number(value.parse::<i64>().unwrap_or(0)));
    } else {
        out.push(Token::Qualifier(value.to_ascii_lowercase()));
    }
}

fn compare_token(a: &Token, b: &Token) -> Ordering {
    match (a, b) {
        (Token::Number(ai), Token::Number(bi)) => ai.cmp(bi),
        (Token::Number(_), Token::Qualifier(_)) => Ordering::Greater,
        (Token::Qualifier(_), Token::Number(_)) => Ordering::Less,
        (Token::Qualifier(aq), Token::Qualifier(bq)) => qualifier_rank(aq).cmp(&qualifier_rank(bq)).then_with(|| aq.cmp(bq)),
    }
}

fn qualifier_rank(value: &str) -> i64 {
    match value {
        "snapshot" => 0,
        "alpha" | "a" => 1,
        "beta" | "b" => 2,
        "milestone" | "m" => 3,
        "rc" | "cr" => 4,
        "" | "final" | "ga" | "release" => 5,
        "sp" => 6,
        _ => 3,
    }
}

fn round_one(value: f64) -> f64 {
    (value * 10.0).round() / 10.0
}

fn render_audit(rows: &BTreeSet<AuditRow>) -> String {
    let mut out = String::from("kind,coordinate,module,detail");
    for row in rows {
        out.push('\n');
        out.push_str(&format!(
            "{},{},{},{}",
            csv_escape(&row.kind),
            csv_escape(&row.coordinate),
            csv_escape(&row.module),
            csv_escape(&row.detail)
        ));
    }
    out
}

fn csv_escape(value: &str) -> String {
    if value.contains(',') || value.contains('"') || value.contains('\n') || value.contains('\r') {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_string()
    }
}

fn json_files(dir: &Path) -> Result<Vec<PathBuf>, String> {
    let mut files = Vec::new();
    for entry in fs::read_dir(dir).map_err(|e| e.to_string())? {
        let path = entry.map_err(|e| e.to_string())?.path();
        if path.extension().and_then(|value| value.to_str()) == Some("json") {
            files.push(path);
        }
    }
    files.sort();
    Ok(files)
}

fn read_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{}: {e}", path.display()))?;
    serde_json::from_str(&text).map_err(|e| format!("{}: {e}", path.display()))
}
