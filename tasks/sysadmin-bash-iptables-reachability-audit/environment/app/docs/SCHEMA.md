# iptables audit — contract & schema reference

The audit pipeline ingests a live iptables-save snapshot and produces a per-rule and per-chain audit. This document specifies the exact contracts every stage upholds. Fields not listed here are unconstrained.

## Upstream envelope

`${API_BASE_URL}/api/iptables-snapshot` returns a JSON object with a `tables` array. Each table has:

- `name` — table identifier (`filter`, `nat`, ...).
- `chains` — array of `{name, kind, default_policy, packet_count, byte_count}`.
  - `kind` is `builtin` or `user_defined`.
  - `default_policy` is populated only for builtins.
- `rules` — array of `{chain, position, matcher_text, target, target_args, jump_kind, packet_count, byte_count}`.
  - `jump_kind` is `jump` (invoke chain, return after) or `goto` (transfer control, no return).

Chain identity is the pair `(table_name, name)`. The same chain name can exist in more than one table as distinct chains.

## Normalized record shape

`/app/data/normalized_iptables.jsonl` interleaves two record types discriminated by `record_type`.

### `chain` records

`table_name`, `name`, `chain_kind`, `default_policy`, `packet_count`, `byte_count`.

### `rule` records

`rule_id` (synthetic `<table_name>.<chain>:<position>`), `table_name`, `chain`, `position`, `target`, `target_args`, `matcher_csv`, `is_unconditional`, `packet_count`, `byte_count`, `target_type`.

- `matcher_csv` is `matcher_text` with surrounding whitespace trimmed.
- `is_unconditional` is `1` when `matcher_csv` is empty, else `0`.

### `target_type` classification

`target_type` is decided in two layers.

**Layer 1 — default classification.** Target names in `/app/api/contracts/target_classification.tsv` map as follows:

- `terminal` — ACCEPT, DROP, REJECT, QUEUE, DNAT, SNAT, MASQUERADE, REDIRECT.
- `non_terminal` — LOG, NFLOG, TRACE, AUDIT, MARK, CONNMARK.
- `return` — RETURN.

If the target is neither built-in nor listed in the catalog, but matches a user-chain name in the rule's OWN table:
- `goto` when `jump_kind == "goto"`.
- `jump` when `jump_kind == "jump"`.

Any other target is `unknown`.

**Layer 2 — local policy overrides.** `/app/api/contracts/local_policy_overrides.tsv` applies on top of the default. Each override row has `match_kind`, `match_value`, `forced_target_type`:

- `log_prefix_contains` — matches when `target == "LOG"` AND `target_args` contains `match_value` as a substring.
- `target_args_contains` — matches when `target_args` contains `match_value` as a substring, regardless of target.

Overrides are applied in file order. The LAST matching override wins.

## Persisted schema

`/app/data/iptables_audit.db` has four tables per `/app/db/schema.sql`.

### `chains`

One row per chain. Carries `table_name`, `name`, `chain_kind`, `default_policy`, `packet_count`, `byte_count`, plus two computed columns:

**`effective_default_policy`.** For `chain_kind == "user_defined"` the value is `return`. For `chain_kind == "builtin"` the value is `preempted` when the chain contains any rule with `is_unconditional == 1` AND `target_type` in `{terminal, goto}`; otherwise the declared `default_policy`. Note that unconditional gotos preempt the default the same way unconditional terminals do — a chain that always transfers control out before its end reaches its declared default zero times.

**`is_dead_chain`.** For `chain_kind == "user_defined"`, `1` when no row in `chain_graph` has both `to_table_name` and `to_chain` matching this chain's `(table_name, name)`, else `0`. Builtin chains are never dead. Dead-chain scope is per-table: a user chain with the same `name` as a user chain in a different table does NOT share inbound coverage.

### `rules`

One row per rule with `rule_id`, `table_name`, `chain`, `position`, `target`, `target_args`, `target_type`, `matcher_csv`, `is_unconditional`, `packet_count`, `byte_count`. Values pass through from the normalized JSONL.

### `chain_graph`

One row per control-transfer edge with `from_table_name`, `from_chain`, `to_table_name`, `to_chain`, `via_rule_id`. Emit one edge per rule whose `target_type` is `jump` OR `goto`. Both `from_table_name` and `to_table_name` are the rule's `table_name` — jump and goto both resolve within the same table.

### `rule_audit`

One row per rule with `rule_id`, `is_reachable`, `blocked_by_rule_id`.

**`is_reachable`** — decided per chain, scoped by `(table_name, chain)`. Walk each group in ascending `position`. A rule at position N is `is_reachable = 0` iff some rule at position M < N in the same `(table, chain)` is `is_unconditional == 1` AND has `target_type` in `{terminal, return, goto}`. `blocked_by_rule_id` records the earliest such M; reachable rules have `blocked_by_rule_id = ""`.

Reachability does not propagate across tables or across chains within the same table. Rules with `target_type == "non_terminal"` do not block subsequent rules. Rules with `target_type == "jump"` do not block the caller — control returns to the caller after the invoked chain completes. Rules with `target_type == "goto"` DO block the caller — `-g` does not set a return point; when the goto'd chain finishes, control returns to the caller's caller, not the caller itself. This holds even if the goto'd chain itself immediately RETURNs.

### `is_effectively_dead_chain`

A user chain is `is_effectively_dead_chain = 1` iff every inbound `chain_graph` edge into it is "non-live". A live inbound edge requires BOTH:

- Its `via_rule` is reachable (`rule_audit.is_reachable = 1`), AND
- Its source chain is itself live — a builtin chain, or a user chain not currently marked effectively dead.

Builtin chains are always `is_effectively_dead_chain = 0`.

The computation is a FIXPOINT. Initialize every user chain to `1`. Repeatedly flip to `0` any user chain that has at least one live inbound edge under the current pass. Continue until no chain's status changes. The transitive case matters: a chain reachable only through a chain that is itself effectively dead is still effectively dead, even though the intermediate rule appears `is_reachable = 1` within its own scope.

## Report shape

`/app/reports/iptables_audit.csv` — header on the first line in this column order:

```
rule_id,table_name,chain,position,target,target_type,is_unconditional,is_reachable,blocked_by_rule_id,packet_count
```

Detail rows come from `rule_audit` joined with `rules`, sorted `(table_name, chain, position)` ascending. Integer columns render as plain integers with no quoting or decimal points; string columns are the literal strings from the DB. `blocked_by_rule_id` is the empty string when a rule is reachable.

Final row is a `TOTAL` row with column 1 = `TOTAL`, columns 2–6 (`table_name`, `chain`, `position`, `target`, `target_type`) empty, column 7 holding the integer sum of `is_unconditional` across all detail rows, column 8 holding the sum of `is_reachable`, column 9 (`blocked_by_rule_id`) empty, column 10 holding the sum of `packet_count`.


## Packet traversal simulation

`/app/api/contracts/probe_packets.tsv` (tab-separated; `#` comments and the header row are skipped) lists probe packets with `probe_id`, `entry_table`, `entry_chain`, `in_iface`, `out_iface`, `proto`, `dport`, `state`. A field value of `-` means the packet does not carry that attribute.

`/app/reports/packet_traces.csv` reports the simulated traversal of each probe. Header, in this exact order:

```
probe_id,entry_table,entry_chain,final_verdict,decided_by,hop_count,path
```

### Matcher evaluation

A rule matches a probe iff EVERY clause in its `matcher_csv` matches:

- `-i <iface>` matches when the probe's `in_iface` equals `<iface>`.
- `-o <iface>` matches when the probe's `out_iface` equals `<iface>`.
- `-p <proto>` matches when the probe's `proto` equals `<proto>`.
- `--dport <n>` matches when the probe's `dport` equals `<n>`.
- `-m state --state A,B` / `-m conntrack --ctstate A,B` matches when the probe's `state` is one of the listed states.
- `-m limit ...` always matches (rate limiting is non-deterministic; for reachability it is treated as pass-through).
- An empty matcher (unconditional rule) always matches.

A clause referencing an attribute the probe carries as `-` does not match.

### Traversal machine

Start at `entry_chain` (always a built-in chain) of `entry_table`, position 1, with an empty return stack. Walk rules in ascending position. For the first rule that matches, act on its `target_type` (the value already stored in the `rules` table, local-policy overrides applied):

- `terminal`: the traversal stops. `final_verdict` is the rule's `target`; `decided_by` is the rule's qualified id.
- `non_terminal`: record the rule and continue to the next position (no verdict).
- `jump`: push a return frame pointing at the NEXT position in the current chain, then descend into the target chain at position 1.
- `goto`: descend into the target chain at position 1 WITHOUT pushing a return frame. Because no return point is left behind, when the goto'd chain returns or falls off its end, control resumes wherever the CURRENT chain would have returned to (the grandparent), never the rule after the goto.
- `return`: in a user chain, pop the return stack and resume the caller; in a built-in chain, apply the chain's default policy as the verdict and stop.
- `unknown`: record the rule and continue.

Running off the end of a chain: a user chain performs an implicit RETURN (pop and resume the caller); a built-in chain applies its default policy as the verdict and stops. If the return stack is empty when a user chain returns or falls off, control has passed back through the entry built-in chain, so the entry chain's default policy is the verdict.

### Columns

- `final_verdict` — the deciding rule's `target`, or the default policy value when a built-in chain's policy fired.
- `decided_by` — the qualified rule id that decided the verdict, or `policy:<table>.<chain>` when a default policy decided it.
- `hop_count` — the number of matched rules recorded during the walk.
- `path` — the pipe-joined (`|`) sequence of matched rule ids in traversal order; empty when no rule matched.

Detail rows are sorted by `probe_id` ascending. The final row is the TOTAL row: the literal string `TOTAL` is the value of the first column, `hop_count` holds the integer sum across all probes, and every other column is the empty string.
