Imports now run as a fleet. When a feed needs loading, several importer processes
can be launched at once for the same feed, each as
`node /app/import.js --feed-key <k> /app/data/<feed>` with the same `<k>` (a retry
storm fans the same job out across processes). Exactly one of them must perform the
import; the rest must recognize the job is already taken and exit without repeating
it. Decoding and writing the feed is unchanged from before, and
`/app/docs/catalog-feed-spec.md` is the contract; what is new is coordinating the
fleet through the `import_runs` ledger.

`import_runs(feed_key text primary key, row_count int, finished boolean)` records
one row per import job. When importers race under the same `feed_key`, exactly one
must claim the key and do the work, then mark its run finished with the `row_count`
it imported; every other process must see the key already claimed and exit 0 having
imported nothing, printing `processed 0 rows` as its final stdout line. The worker
that wins prints `processed <N> rows`. The claim has to be atomic: two importers
that start at the same instant must never both decide they are the one to run, and
no process may crash because another already recorded the run.

End state, with a small catalog feed loaded under one `--feed-key <k>` by several
concurrent processes: every process exits 0, exactly one prints `processed <N> rows`
and the rest print `processed 0 rows`, `import_runs` holds exactly one finished row
for `<k>` whose `row_count` is `<N>`, and `products` holds the `<N>` decoded
records. Connect with `sudo -u postgres psql -p 5433 -d app`.
