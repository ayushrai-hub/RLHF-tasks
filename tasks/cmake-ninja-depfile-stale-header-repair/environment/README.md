# Depfix demo build

Small C++/CMake/Ninja workspace used to validate custom depfile normalization and incremental rebuild behavior.

- Sources: `/app/src/`, headers: `/app/include/depfix/`
- Build support: `/app/build_support/depfix.cmake`, `/app/build_support/depfix_normalize.cmake`
- Configure: `cmake -G Ninja -S /app -B /app/build`
- Build: `ninja -C /app/build`
- Public touch sample: `/app/fixtures/touch_order.json`
- Depfile contract: `/app/docs/ninja_depfile_format.md`
- Rebuild contract: `/app/docs/rebuild_expectations.md`
- Audit report schema: `/app/docs/audit_report_schema.md`
