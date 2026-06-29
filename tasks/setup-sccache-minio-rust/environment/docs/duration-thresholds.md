# Duration thresholds

Record integer-second wall times with `date +%s` for all three benchmark phases. Warm phases under one second may round to zero in the release gate report.

Cold should reflect a first fill with a non-zero miss count. Warm may finish in less than half the cold duration with small non-zero miss counts while metadata settles. Post-clean should show cache hits after local `target/` trees are removed.

Replay verification is optional on staging hosts.
