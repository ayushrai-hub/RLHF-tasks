The diffusion workbook import path is broken in two places. `/app/workbook/migrations/001_import.js` does not load nested sweep JSON correctly, and `/app/workbook/lib/go-resolve.js` does not walk chained Go `replace` directives under `/app/workbook/kernels/`.

Fix both per `/app/workbook/docs/import-contract.md`. The contract overrides legacy notes in `/app/workbook/kernels/README.md` and `kernel-registry.toml`. Run `/app/workbook/bin/migrate.sh` when you are done.
