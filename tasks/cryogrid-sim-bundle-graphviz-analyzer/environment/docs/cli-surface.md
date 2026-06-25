# CLI surface

Binary: /app/build/cryogrid-analyze

## analyze

```text
/app/build/cryogrid-analyze --spec <bundle.json> --out-dir <dir>
```

Optional: --memo-dir defaults to /app/docs/validation-memo (reserved for future memo checksums).

Reads an OCI-style CryoGrid simulation bundle, computes per-stage variance using rules in
/app/docs/validation-memo/cryogrid-thermal-review.md, detects unstable feedback loops,
writes /app/output/uncertainty-graph.dot and /app/output/metrics-report.json when --out-dir
is /app/output.

Exit 0 on success. Exit non-zero on parse or I/O errors.

Environment override CG3_BUNDLE_ROOT may point to an absolute directory of bundle fixtures
for integration tests.

## Build

```text
cmake -B /app/build -S /app && cmake --build /app/build
```

LegacyDotWriter under /app/src/legacy_dot_writer.cpp is not part of the analyze path.
