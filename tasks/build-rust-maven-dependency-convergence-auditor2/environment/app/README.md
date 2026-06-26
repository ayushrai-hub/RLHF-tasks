# Maven Dependency Convergence Fixtures

The CLI reads `/app/fixtures/policy/dependency-policy.json` and JSON module manifests under `/app/fixtures/modules`.

## Policy Fields

- `bannedLicenses`: license identifiers rejected for non-ignored dependencies.
- `criticalCvss`: CVSS threshold for critical CVE findings.
- `ignoredScopes`: scopes ignored for policy checks.
- `activeProfiles`: module profile IDs included in the audit.
- `suppressedCves`: CVE IDs ignored globally.
- `licenseAliases`: raw license names to canonical identifiers.
- `properties`: property names available to policy-managed versions and module manifests.
- `managedVersions`: effective coordinate to managed version mapping.
- `minimumVersions`: effective coordinate to minimum accepted version mapping.
- `relocations`: raw coordinate to effective coordinate mapping.
- `boms`: named BOM maps from effective coordinate to version.
- `alignmentGroups`: named coordinate sets checked for selected-version alignment.

## Module Fields

- `module`: module identifier.
- `properties`: optional property values scoped to the module.
- `imports`: optional policy BOM names.
- `dependencyManagement`: optional coordinate to managed version mapping.
- `profiles`: optional profile records with `id`, scoped properties/imports/management, and dependencies.
- `dependencies`: dependency records used by the audit.

## Audit CSV Notes

`dependency-audit.csv` uses the header `kind,coordinate,module,detail`. Artifact-level rows use the effective coordinate in `coordinate` and the literal `*` sentinel in `module`. `module_summary` rows use an empty `coordinate` and the module name in `module`. `license_summary` rows use the license name in `coordinate` and `*` in `module`. For `managed_version_mismatch`, `actual=` lists every differing non-ignored concrete effective version joined by `|`.
