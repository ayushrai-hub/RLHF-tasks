The `pc-sanitize` tool reads pkg-config `.pc` files and a small JSON manifest, then writes deterministic JSON reports. The supported commands are:

`pc-sanitize parse --pc-dir DIR --manifest FILE --out FILE`
`pc-sanitize resolve --pc-dir DIR --manifest FILE --out FILE`
`pc-sanitize audit --pc-dir DIR --manifest FILE --out FILE`

The manifest has `roots`, `allowed_static_flags`, and `static_only_flags` arrays. Output arrays are sorted by package or root name unless the contract says dependency traversal order matters. Missing optional `.pc` fields become empty strings or empty arrays. Version constraints in `Requires` and `Requires.private`, such as `zlib >= 1.2`, are ignored after the package name is extracted.

The parse report is an object with `packages` and `errors`. Each package object has `name`, `version`, `description`, `requires`, `requires_private`, `libs`, `libs_private`, and `cflags`. Variables such as `${libdir}` and `${prefix}` must be expanded before flags are tokenized.

The resolve report is an object with `roots`. Each root object has `name`, `public_libs`, `static_libs`, and `dependency_edges`. Public libraries include the root package and its transitive public `Requires`. Static libraries also include each visited package's `Libs.private` and transitive `Requires.private`. Edges use objects with `from`, `to`, and `kind`, where `kind` is `public` or `private`.

The audit report is an object with `findings` and `summary`. A `leaked_static_flag` finding is emitted when a package's public `Libs` includes a manifest `static_only_flags` token, an archive path ending in `.a`, or `-Wl,--whole-archive`, unless that token is listed in `allowed_static_flags`; its detail is the leaked token. A `missing_dependency_edge` finding is emitted when a package links `-lNAME` publicly or privately and another scanned package advertises that library as its package name or one of its public libraries, but neither `Requires` nor `Requires.private` names that package; its detail is exactly `-lNAME should be declared as dependency PACKAGE`, using the linked flag and provider package name. Findings are sorted by package, then kind, then detail. The summary has `total`, `by_kind`, and `affected_packages`.
