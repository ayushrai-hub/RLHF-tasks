# Settlement Format

The raw event files under `/app/raw-events` use one JSON object per line. Meter metadata, account energy rates, and district credits are stored in `/app/catalog/meter_catalog.db`.

Normalized event rows are consumed by downstream billing systems as JSON Lines. Settlement output is split between a SQLite database for account-month lookup and a JSON summary for daily review.

Reconciliation is a separate final review step. It compares the current account-month settlement rows with the prior ledger snapshot and applies manual adjustments from the catalog database without changing the settlement database.
