The catalog has a second source now: a change-log container at
`/app/data/changelog.bin`. Instead of a full snapshot it records edits over time,
and the importer must fold it down to the final state of each product. You add this
mode and run it as `node /app/import.js --changelog /app/data/changelog.bin`.

The change-log container frames its records differently from the catalog feeds, so
a catalog decoder will not parse it as-is; in this container each record is bound to
the one before it, so the records have to be decoded in order and one wrong record
throws off the rest. As before, `/app/ref/catalog-probe /app/data/changelog.bin`
decodes a container to JSON so you can see the records it should produce, and
`/app/docs/catalog-feed-spec.md` is the behavioural contract. The probe is a study
aid and is not present in production, so the importer must decode the change-log
itself.

Each decoded record carries `id`, `version`, an `op` of `put` or `del`, and the
product fields, any of which may be absent in a `put`. A product has one record per
version and the container is shuffled, so container order is not version order. Fold
each product over its versions in version order: a `del` is a tombstone that removes
everything before it, so a product deleted and later `put` again starts fresh from
after that tombstone; for a surviving product each column takes the value from the
highest-version `put` after the last tombstone whose cell for that column is present
(an absent cell leaves that column unchanged); and a product whose latest version is
a `del` does not appear at all. After `node /app/import.js --changelog /app/data/changelog.bin`,
`products` holds exactly the reconciled set, one row per surviving product. The
change-log is large and the heap is still capped at 64 MB, so reconcile it in a
single streaming pass that keeps only per-product state. Connect with
`sudo -u postgres psql -p 5433 -d app`.
