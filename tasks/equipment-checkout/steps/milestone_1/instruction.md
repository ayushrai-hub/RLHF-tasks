# Milestone 1 — Database Setup and Equipment/Borrower Management

Build the Go CLI at `/app/app` using `go build -o /app/app .` from `/app`. The database path is the first positional argument after the command name.

## Commands

### `init <db>`
Create the SQLite database and all four tables (`equipment`, `borrowers`, `checkouts`, `audit_chain`) if they do not already exist. Running `init` twice is safe. See `/docs/schema.md` for column definitions. Prints `OK`.

### `add-equipment <db> <equipment_id> <name> <category> <daily_rate_cents> [condition]`
Insert equipment. `category` must be one of: `tool`, `electronics`, `furniture`.
The optional `condition` argument must be one of: `OK`, `DAMAGED`, `MAINTENANCE`. If omitted, defaults to `OK`.
- Success: `OK`
- Duplicate `equipment_id`: print `equipment already exists: <equipment_id>` to stdout and exit 1.
- Invalid category: print error to stdout and exit 1.
- Invalid condition: print error to stdout and exit 1.

See `/docs/equipment-policies.md` for the rules governing each condition value.

### `add-borrower <db> <borrower_id> <name>`
Insert a borrower. Names may contain spaces.
- Success: `OK`
- Duplicate `borrower_id`: print `borrower already exists: <borrower_id>` to stdout and exit 1.

### `list-equipment <db>`
Print all equipment ordered by `equipment_id` ASC, one per line, tab-separated:

    <equipment_id>\t<name>\t<category>\t<daily_rate_cents>\t<status>\t<condition>

`status` is `available` or `checked_out`. `condition` is `OK`, `DAMAGED`, or `MAINTENANCE`. Print nothing if no equipment exists.

## References
Schema: `/docs/schema.md` — Chain spec: `/docs/chain-spec.md` — Equipment policies: `/docs/equipment-policies.md`
