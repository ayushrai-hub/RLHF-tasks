# Lockfile and report schema

## Lockfile

Top-level object with exactly one key, `packages`, whose value is an array of
package objects. Packages are sorted by `name`.

Each package object uses this field order:

| Field | Type |
|-------|------|
| `name` | string |
| `version` | semver string |
| `features` | array of strings, sorted lexically |
| `dependencies` | array of dependency objects, sorted by `name` |

Each dependency object uses this field order:

| Field | Type |
|-------|------|
| `name` | string |
| `version` | semver string |

Encode with UTF-8, two-space indentation, and one trailing newline.

## Report

Top-level object with exactly one key, `conflicts`, whose value is an array of
conflict objects. Conflicts are sorted by `package`.

Each conflict object uses this field order:

| Field | Type |
|-------|------|
| `package` | string |
| `constraints` | array of semver requirement strings, sorted lexically |
| `reason` | string (e.g. `no matching version`) |

Encode with UTF-8, two-space indentation, and one trailing newline.
