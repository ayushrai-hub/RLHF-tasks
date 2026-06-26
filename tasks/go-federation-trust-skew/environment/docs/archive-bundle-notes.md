# Archive bundle notes

Historical tuning notes from an older LRU cache experiment.

Increasing cache capacity from 128 to 512 entries reduced p99 lookup latency in staging but did not change admission outcomes. Prefetching bundle rows on daemon start similarly only shifted dashboard counters.

When investigating admission regressions, start with spool ledger generation counters and alias table reload ordering before resizing caches or editing meter rollup counters.
