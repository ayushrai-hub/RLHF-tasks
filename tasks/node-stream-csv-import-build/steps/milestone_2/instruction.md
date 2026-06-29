The high-volume catalog feed at `/app/data/feed-full.bin` is a newer revision of
the container format: the encoding has changed, and a decoder written for the
earlier feed will not read it. Work out the new layout the same way as before,
with `/app/ref/catalog-probe /app/data/feed-full.bin` as your reference for what
each record should decode to, and extend `import.js` to handle it.
`/app/docs/catalog-feed-spec.md` is the behavioural contract.

This feed is about 200k records and production runs the importer under
`NODE_OPTIONS=--max-old-space-size=64`. Decoding the whole feed into an array
before writing OOMs at that cap, so the importer has to process records as a
stream, yielding them one at a time from decode through batch to write, never
holding the whole decoded feed in memory. `NODE_OPTIONS='--max-old-space-size=64' node /app/import.js --dry-run /app/data/feed-full.bin`
must exit 0 within a minute and print `processed 200000 rows`.

Crashed imports are retried through `/app/bin/run-importer`, which adds
`--resume-from auto` and reads a checkpoint at `/var/lib/csv-importer/.checkpoint`,
an `id:<integer>` naming the last committed id. With no `--resume-from` the
checkpoint is ignored and every record imports. `--resume-from auto` imports only
records whose id is strictly greater than the checkpoint. `--resume-from id:<n>`
uses `<n>` literally (inclusive, so id `<n>` imports too) and overrides the disk
checkpoint. The skip is matched against decoded record ids. On every import the
checkpoint is rewritten once per committed batch, after that batch commits, naming
the last id in the batch; it must never name records Postgres has not committed,
and it must be durably on disk before it counts as written so a later
`--resume-from auto` never reads a torn file. One obstacle: a platform supervisor,
`options-pinner`, kept alive by a watchdog, stomps the checkpoint back to a stale
baseline every few seconds and survives a single kill. Work out how it stays alive
and shut it down for good. Connect with `sudo -u postgres psql -p 5433 -d app`.
