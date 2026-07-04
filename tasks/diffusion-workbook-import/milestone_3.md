Summary rows look plausible, but the checksum in `/app/workbook/reports/diffusion_report.md` does not match a fresh migration run.

Fix `/app/workbook/lib/export-checksum.js` per `/app/workbook/docs/checksum-contract.md` so `/app/workbook/out/summary.checksum` reconciles with the report. Run `/app/workbook/bin/migrate.sh`, then `/app/workbook/bin/verify-report.sh`.
