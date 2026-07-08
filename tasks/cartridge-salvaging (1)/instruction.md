You are recovering data from forty failing cartridges, `T01` through `T40`. For each one you commit up
front a fixed number of read attempts, and the plan then runs exactly as written — you cannot watch an
attempt come back empty and decide to add another. An attempt either pulls a clean, hash-verified image
or recovers nothing, so if a single attempt on a cartridge succeeds with that cartridge's own chance
`p`, a plan of `n` attempts saves it with chance `1 - (1 - p)^n`. Every `p` is particular to its
cartridge, and you are never told any of them.

Two things point at `p`. Each cartridge has a `read_margin`, a diagnostic that runs higher when the
medium still tracks cleanly, and `/app/data/read_log.csv` lists the triage attempts already made, each
row giving a `cartridge_id` and a `verified` flag that reads `1` for a clean attempt or `0` for a
failed one; some cartridges have several rows and others none. Grading does not use those rows. It
re-reads all forty cartridges for real and scores each against its true hidden `p`, and the whole run
is judged by its weakest cartridge, the one your counts leave with the lowest recovery chance, which
has to reach `recovery_floor`. Because that score turns on the hidden rate rather than the figure you
report, and you cannot tell going in which cartridge will decide it, size each cartridge from a cautious
low estimate of its rate, not the reading it first presents. A high `read_margin`, or a short log that
happened to verify clean, can flatter a rate that little evidence actually pins down; where a cartridge
gives you least to stand on, the safe count is the more generous one.

Two costs bound the plan. Bench attempts on the shared drive rig are cheap but capped at
`bench_capacity` in total; past that you fall back to an uncapped, costlier dedicated rig, and the
plan's committed cost may never exceed `cost_ceiling`. Each row of `/app/data/cartridges.csv` gives a
cartridge's `cartridge_id`, its `read_margin`, and its two prices `cost_bench` and `cost_lab`, while
`/app/data/salvage_program.json` holds `reference_margin`, `recovery_floor`, `bench_capacity`,
`cost_ceiling`, plus `rate_min` and `rate_max`, which fix how low or high any rate you settle on may
go. Write `/app/output/recovery_plan.csv` with one row per cartridge and columns `cartridge_id`,
`bench_passes`, `lab_passes`, each a non-negative integer; and `/app/output/kpis.json` reporting
`total_committed_passes`,
`total_bench_passes`, `total_lab_passes` as integers, `committed_cost` as a float, and
`worst_cartridge_recovery_prob` — your expected recovery chance at the weakest cartridge — as a float
in [0, 1]. Use only the shipped Python and numpy; there is no network.
