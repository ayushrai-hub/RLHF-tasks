# Checksum contract

After migrations, `/app/workbook/lib/export-checksum.js` writes `/app/workbook/out/summary.checksum`.

Serialize every row in `diffusion_summary` sorted by `sweep_id` ascending. Each line is compact JSON with keys in this order: `sweep_id`, `kernel_revision`, `diffusion_coeff`, `rss`. Numeric fields use six decimal places as strings in the JSON number position (e.g. `0.500000`).

Join lines with `\n` (no trailing newline). SHA-256 hex digest of the UTF-8 body is the checksum.

`/app/workbook/reports/diffusion_report.md` must contain a line `checksum: <hex>` matching that digest after a clean migration run.
