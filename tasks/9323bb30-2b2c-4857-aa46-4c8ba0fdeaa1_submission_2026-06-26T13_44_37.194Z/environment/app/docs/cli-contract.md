# CLI contract

## vaultshard-ingest

```
/app/bin/vaultshard-ingest --db <path> --bundle <path>
```

- `--db` defaults to `/app/data/vault.db`
- `--bundle` path to a `.vshard` file (required)

Exit `0` on success. Non-zero on parse/CRC/constraint errors (database unchanged on rollback).

## vaultshard-export

```
/app/bin/vaultshard-export --db <path> --tenant-id <id> [--out <path>]
```

- `--db` defaults to `/app/data/vault.db`
- `--tenant-id` required
- `--out` defaults to `/app/output/vault-hotreload-audit.json`

Exit `0` on success.

## Build

`/app/scripts/build.sh` compiles Scala sources when `VAULT_BUILD_CHECK` is unset. When `VAULT_BUILD_CHECK=1`, only verifies `/app/bin/app.jar` exists.
