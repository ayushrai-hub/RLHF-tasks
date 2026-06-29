# Projectile ballistics (`ballctl`)

Workspace under `/app` with library crate `ballcore` and CLI `ballctl`.

## Toolchain

- **Preinstalled:** `/usr/local/cargo/bin/cargo`, `/usr/local/bin/ballctl` (release build from image).
- **Do not** run `apt-get install` for Rust; the sandbox has no package mirrors for that path.
- After code changes: `cargo build --release --locked -p ballctl` then `install -m 0755 /app/target/release/ballctl /usr/local/bin/ballctl`.

## Commands

Two-step single shot (required for audit export):

```bash
ballctl integrate-shot \
  --stack /app/fixtures/stacks/multi-layer.json \
  --materials /app/fixtures/materials/catalog.json \
  --velocity 0,0,-420 \
  --energy 3200 \
  --seed 42

ballctl export-shot --export /app/output/shot.json
```

See `/app/docs/export-shot-contract.md`. Legacy one-step `simulate-shot` exists but does not follow staged export rules.

Batch (multi-tick):

```bash
ballctl simulate-batch \
  --batch /app/fixtures/batches/two-tick.json \
  --materials /app/fixtures/materials/catalog.json \
  --stacks-dir /app/fixtures/stacks \
  --export /app/output/batch.json
```

Seed values index `/app/fixtures/seeds.json` and scale incident velocity magnitude before integration.

Contracts: `/app/docs/`. Fixture index: `/app/fixtures/catalog.json`.

Rebuild after code changes:

```bash
cargo build --release --locked -p ballctl
install -m 0755 /app/target/release/ballctl /usr/local/bin/ballctl
```
