# interval-meter batch reconciler

C batch tool under `src/` reads interval register CSV exports, applies TOU schedules from `config/tariffs.json`, and writes JSON reconciliation output.

Build: `make -C /app/environment`

Run: `/app/bin/tou_reconcile --config /app/environment/config/run.json --out /app/output/reconciliation_report.json`

See `docs/operations.md` and `docs/tariff_rules.md` for field definitions.
