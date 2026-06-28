# Incremental rebuild expectations

## Header sync stamp

`depfix_header_sync` is a phony target backed by `/app/build/depfix_header.stamp`. The stamp rule must list **both** `/app/include/depfix/config.hpp` and `/app/include/depfix/version.hpp` as inputs so either header invalidates the stamp.

`depfix_util`, `depfix_core`, and `depfix_app` must depend on `depfix_header_sync` in the Ninja graph.

## Touch outcomes

Touching `/app/include/depfix/config.hpp` must rebuild at least `CMakeFiles/depfix_util.dir/src/util.cpp.o` before the app links.

Touching `/app/include/depfix/version.hpp` must rebuild at least `CMakeFiles/depfix_core.dir/src/core.cpp.o`.

Touching `/app/include/depfix/legacy_alias.hpp` must rebuild at least `CMakeFiles/depfix_util.dir/src/util.cpp.o`.

Touching `/app/include/depfix/config.hpp` must also relink `/app/build/depfix_app` after util objects rebuild.

## Compiler dependency flags

The `depfix_util` library and `depfix_app` executable compile rules must pass `-MD` and `-MP` so Ninja generates phony headers for missing dependency targets during incremental builds.

## Audit CLI

The audit tool replays fixture touch lists, runs `ninja -C /app/build` after each touch, and records rebuilt outputs parsed from `/app/build/.ninja_log`. Semantics are documented in `/app/docs/audit_report_schema.md`.
