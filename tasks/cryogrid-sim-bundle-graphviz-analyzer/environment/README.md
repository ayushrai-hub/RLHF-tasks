# CryoGrid OCI uncertainty analyzer

CMake project that loads OCI-style simulation bundle JSON, applies variance rules from
the long-form validation memo under /app/docs/validation-memo/, and emits Graphviz DOT
plus a JSON metrics report.

Build: cmake -B /app/build && cmake --build /app/build

Binary: /app/build/cryogrid-analyze

See /app/docs/cli-surface.md and /app/docs/metrics-schema.md.
