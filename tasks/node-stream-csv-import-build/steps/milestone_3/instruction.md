The nightly snapshot feed at `/app/data/feed-snapshot.bin` encodes its numeric
fields differently from the earlier feeds, so a decoder that reads `qty` and
`price` straight gets them wrong on every record. Work out the new numeric encoding
with `/app/ref/catalog-probe /app/data/feed-snapshot.bin` as your reference for the
true values, so `qty` and `price` match the probe. The text fields and the framing
are unchanged from the previous feed. `/app/docs/catalog-feed-spec.md` is the
behavioural contract.

The importer must also be idempotent. Because every batch names the record `id`,
importing the snapshot twice after a clean truncate must converge rather than die
on the first batch with `duplicate key value violates unique constraint
"products_pkey"`. Repeated imports of the same snapshot must converge, and when a
row's `qty`, `name`, `sku`, or `price` has drifted between the feed and Postgres,
the next import must land the feed value back into the existing row.

Two more rules. A decoded text field can be absent (the probe shows it with no
value) as opposed to a present string: when a record's `sku` or `name` is absent,
leave the existing Postgres value alone, but a present value overwrites it. (`qty`
and `price` are always taken from the feed.) And because every batch inserts an
explicit `id`, the identity sequence behind `products.id` never advances, so the
next operator `INSERT` without an id collides on `id=1`; leave that sequence at the
post-import maximum by the time the importer exits, so such an `INSERT` returns
`MAX(id) + 1`. That is the importer's own job, not a separate sweeper. Target, all
against `/app/data/feed-snapshot.bin`: a clean import (truncate first) exits 0,
prints `processed 200000 rows`, and an `INSERT INTO products (sku, name, qty, price)
VALUES ('NEW-SKU', 'placeholder', 1, 1.0) RETURNING id` right after returns 200001;
a second back-to-back import exits 0 with the count unchanged. Connect with
`sudo -u postgres psql -p 5433 -d app`.
