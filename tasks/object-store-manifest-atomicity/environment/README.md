# Offline object-store manifest tool

`ostore` rebuilds a compact manifest, checksum report, and provenance record from a local filesystem object-store tree. The tool is local-only and uses the Go standard library.

## Useful local commands

```bash
cd /app/environment
make build
make replay-smoke
/app/environment/bin/ostore --help
/app/environment/bin/ostore fixture --scenario crash-retry --store /app/work/object-store
/app/environment/bin/ostore rebuild --store /app/work/object-store --out /app/output
/app/environment/bin/ostore doctor --store /app/work/object-store
```

`make replay-smoke` removes `/app/work/object-store` and `/app/output`, creates a deterministic crash/retry fixture, runs the product rebuild path, and then runs a narrow smoke check. The smoke check is intentionally shallow and is useful only as a local sanity check while working on the CLI.
