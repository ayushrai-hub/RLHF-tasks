# Operators

Rebuild after editing sources under `/app/environment`:

`bash -lc 'go build -C /app/environment -o /app/bin/registeraudit /app/environment/cmd/registeraudit'`

Run practice audit:

`/app/bin/registeraudit audit -mreg-dir /app/environment/fixtures/practice -segment 3 -json-out /app/out/mreg_audit.json`
