# Resolver contract

Invoke the CLI as:

```text
crateledger --workspace <absolute-file> --registry <absolute-dir> --lock <absolute-file> --report <absolute-file>
```

All four paths must be absolute. The workspace file and registry directory must
exist before resolution begins.

| Exit code | Condition |
|-----------|-----------|
| 0 | Resolution succeeded; lock and report written |
| 2 | Usage/input failure, malformed records, missing package, or resolution conflict; a conflict report is written and any existing lockfile is left byte-for-byte unchanged |
| 1 | Other output failure (I/O error); any existing lockfile is left byte-for-byte unchanged |

Diagnostics go to stderr. Successful runs do not write to stdout.

The workspace file is line-oriented; blank lines and `#` comments are ignored.
Each root request has the form:

```text
root <alias> <package> <constraint> [features=a,b,c]
```

`alias` is the name used by the workspace, and `package` is the canonical
package name in the registry.

Each registry package lives at `<registry>/<package>.pkg`. Files are
line-oriented, with blank lines and `#` comments ignored. A version record
starts with `version <semver> [yanked=true]`; following `dep` and `feature`
lines belong to the most recent version.

## Version selection

Yanked versions are never selected. Pre-release versions sort below their
corresponding final release — for example, `1.1.0-alpha` sorts below `1.1.0`,
so a pre-release can satisfy a `<` constraint against the final version while
the final version cannot. The highest non-yanked version that satisfies every
active constraint is selected. When no non-yanked version satisfies all
constraints for a package, the conflict reason is `no matching version`.

The lockfile and report schemas are described in `lock-schema.md`.

The resolver must work entirely offline and produce byte-identical output for
identical inputs. Successful runs create missing parent directories for the
requested lockfile and report paths.
