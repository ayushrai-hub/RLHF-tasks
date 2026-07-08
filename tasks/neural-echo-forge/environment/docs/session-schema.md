# Session and tool schemas

## Session JSONL row

| Field | Type | Required |
|-------|------|----------|
| session_id | string | yes |
| turn_seq | integer | yes |
| anchor_ms | integer | yes, non-negative |
| role | string | yes |
| text | string | optional |
| memory | object | optional |
| correction | object | optional |

## memory object

| Field | Type | Required |
|-------|------|----------|
| memory_id | string | yes |
| subject | string | yes |
| predicate | string | yes |
| object | string | yes |
| confidence | number | yes |
| tier | string | ephemeral, short, or long |

## correction object

| Field | Type | Required |
|-------|------|----------|
| targets | string | yes, non-empty memory_id |
| becomes | string | optional, non-empty memory_id |
| subject | string | yes |
| predicate | string | yes |
| object | string | yes |
| confidence | number | yes |
| tier | string | ephemeral, short, or long |

Corrections inherit anchor_ms and session_id from the parent row. The targets field names the memory_id this correction supersedes. During ingest the correction memory_id is the becomes value when that field is present and non-empty; otherwise it is the targets string, which replaces the target in place. A correction with a distinct becomes memory_id can itself be superseded by a later correction that targets that becomes value, forming a correction chain.

A correction removes its targeted memory_id from the group only when that target is present among the non-correction survivors in the correction's own subject and predicate group at some point during ingest resolution; the target may be produced by an earlier correction in a chain. Corrections whose target never becomes present, including targets that exist only in another group and cyclic corrections that would only satisfy one another, are moved to superseded_memories and do not compete. Applied corrections compete under the temporal precedence rules in conflict-resolution.md. Correction resolution runs to a fixpoint as described in conflict-resolution.md.

## Tool JSONL row

| Field | Type | Required |
|-------|------|----------|
| tool | string | yes |
| anchor_ms | integer | yes |
| memory_id | string | yes |
| subject | string | yes |
| predicate | string | yes |
| object | string | yes |
| confidence | number | yes |
| tier | string | yes |

Tool rows use source tool_invoke. Assign discovery_seq only when a tool row yields an appended candidate, after all profile candidates and in tool file line order.

Text-only session rows may include anchor_ms and contribute to reference_anchor_ms but must not receive discovery_seq and must not increment lines_skipped.

## Profile file

Top-level profiles array. Each profile entry contains user_id, subject, and baseline array. Each baseline item has predicate, object, confidence, and tier fields.

Profile baselines do not carry a memory_id in the input file. During ingest, assign memory_id using this exact format: profile- plus the profile subject string with every colon replaced by a hyphen, plus a hyphen, plus the baseline predicate string. For subject user:alice and predicate timezone, the memory_id is profile-user-alice-timezone. Profile rows use anchor_ms 0, discovery_seq starting at 0 in profile file order, and source profile_baseline.
