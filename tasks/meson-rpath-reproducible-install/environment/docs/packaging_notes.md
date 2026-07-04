# Packaging notes

The project deliberately keeps a checked-in compatibility header for editor tooling and legacy source-tree scans. The shipped header is expected to describe the configured release package. Maintainers normally verify install artifacts rather than relying on a build-directory smoke result.

Release audits enumerate prefix-relative install paths such as `bin/capsule-info`, `bin/capsule-consumer`, `include/capsule.h`, and the configured header under `include/capsule_config.h`. Installed executables are expected to embed `$ORIGIN/../lib` for libexec-style layouts.
