I need an importer at `/app/import.js` that loads upstream product feeds into
PostgreSQL. The feeds live under `/app/data` as binary containers (for example
`/app/data/sample.bin` and `/app/data/catalog.bin`) in an upstream-proprietary
format that is not documented anywhere; there is no plain-text export to fall back
on, and `import.js` ships only as a skeleton that does not yet decode a feed.

What you do have is a reference
decoder at `/app/ref/catalog-probe`: give it a container and it prints the decoded
records as JSON, for example `/app/ref/catalog-probe /app/data/sample.bin`. Use it
to work out how a container is laid out and how each field is encoded, then teach
`import.js` to decode the feed itself and write every record, with every column,
into `public.products`. The probe is a study aid for understanding the format; it
is not part of the importer and will not be present when the importer runs in
production, so the importer must decode feeds on its own and keep working on feeds
it has not seen, not just the samples here. `/app/docs/catalog-feed-spec.md` is the
behavioural contract (the database, the command surface, the record fields).

End state: `node /app/import.js --dry-run /app/data/sample.bin` exits 0 with
`processed <N> rows` as its final stdout line, where `<N>` is the number of records
in that container. After `TRUNCATE products`, `node /app/import.js /app/data/catalog.bin`
exits 0, `SELECT count(*) FROM products` returns 200000 with no NULL `qty`, and the
stored `id`, `sku`, `name`, `qty`, and `price` match what the probe decodes for each
record. Connect to Postgres with `sudo -u postgres psql -p 5433 -d app`.
