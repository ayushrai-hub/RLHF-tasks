Our airgapped fleet has no single source of truth for host state. Three surfaces
under `/app/environment` disagree: cached probes in `r1/` (several generations
per host, some stale), an authority-signed baseline snapshot in `r2/` with a
detached signature, and operator overrides in `r3/` (including retire entries and
entries that alias one host to another). A bash toolchain under
`/app/environment/w7` already reconciles these into a canonical inventory — but
it is **buggy**, and the inventory it regenerates today is wrong.

Run it and check it:

```bash
bash /app/environment/w7/run_entry.sh
/app/environment/r5/inv_verify --all-hosts --inventory-out /app/output/inventory_out.json --report-out /app/output/reconcile_report.json
```

The pipeline runs to completion and produces `/app/output/inventory_out.json`
and `/app/output/reconcile_report.json`, but the result does not satisfy the
contract: some hosts resolve to the wrong claim, the provenance digest does not
reconcile between the inventory and the report's conflict `ledger`, and some
hosts are neither kept among the surviving `records` nor listed in the `retired`
removals the way they should be. Your job is to **find and fix the faults in the
reconciliation source under `/app/environment/w7`** (the modules it wires in
under `/app/environment`), so that a normal run regenerates a correct inventory.

`/app/environment/r6/run_contract.md` is authoritative for the two output schemas,
the provenance-digest formula, and the recovery rule. `/app/environment/r6/rules_contract.md`
defines how the surfaces rank when they disagree, how probe freshness is judged,
how each field (a host's role and its region) is resolved independently by
authority, how the signature gates the baseline, and how aliases and removals
behave. Read both, compare them against what the code actually does, and correct
the code.

The repair belongs in the source under `/app/environment`. A statically written,
precomputed, or hardcoded inventory is insufficient, and so are a wrapper around
`inv_verify`, a stage-only reporter, editing the tests, or mutating the read-only
signed baseline at `/app/environment/r2/base0.json`. The normal pipeline must
regenerate the artifacts, and the signed baseline must stay byte-for-byte
unchanged with its signature still verifying. Recovery after the destructive
re-sync in `/app/environment/r7/rst_step.sh` is the idempotent command named in
`run_contract.md`; the sampled excerpts under `/app/output/logs` are incomplete,
so trust the authoritative surfaces `r1/`, `r2/`, and `r3/`.
