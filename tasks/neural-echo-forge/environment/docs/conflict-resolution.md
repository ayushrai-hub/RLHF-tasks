# Conflict resolution

Group candidate memories by subject and predicate strings exactly as written.

## Correction precedence

A correction row carries a supersession target, given by its targets string, and a resulting memory_id. The resulting memory_id is the correction's becomes value when that field is present and non-empty; otherwise the correction reuses the targets string as its own memory_id and replaces the target in place. In both cases the correction competes as a normal session_correction candidate once it applies.

When a correction applies, remove the targeted memory_id from the candidate pool, move it to superseded_memories, and add the correction under its resulting memory_id. Correction precedence applies only to the targeted memory_id; it does not override temporal ordering against other candidates in the group.

Correction application is resolved to a fixpoint within each subject and predicate group. A correction applies only when its target is currently present among the non-correction survivors of that group. Corrections may chain: the resulting memory_id of one correction can be the target of a later correction, so a correction whose target is not present initially must still apply once an earlier correction produces that memory_id. Iterate correction application until no further correction can apply.

The target must resolve within the correction's own subject and predicate group. A memory_id that appears only in a different subject or predicate group is not a valid target. Corrections whose target never becomes present during this iteration are all moved to superseded_memories without joining temporal precedence: this includes targets that never appear, targets that exist only in another group, and cyclic corrections whose targets would only ever be satisfied by one another.

After correction application reaches its fixpoint, run standard temporal precedence across all remaining candidates including any applied correction rows. The phrase relative to the target means the correction may displace the target even when the correction anchor_ms is lower than the target anchor_ms; it does not exempt the correction from competing with other memories on anchor_ms.

### Worked example (drink_pref)

In subject user:alice and predicate drink_pref, suppose mem-001 (anchor_ms 1100), mem-002 (anchor_ms 800), a correction targeting mem-001 (anchor_ms 2000), and mem-004 (anchor_ms 2100) are present. Step one: mem-001 moves to superseded_memories. Step two: temporal precedence among mem-002, the correction row, and mem-004 selects mem-004 as the group winner because 2100 is the highest anchor_ms under closed conflict_mode.

### Worked example (correction chain)

In one subject and predicate group, suppose base memory mem-a is present, a correction with targets mem-a and becomes mem-b applies first and supersedes mem-a, and a second correction with targets mem-b and becomes mem-c then applies and supersedes mem-b. The surviving candidate is mem-c; mem-a and mem-b are both in superseded_memories. A resolver that only considers the memory_ids observed before any correction applied would wrongly stop at mem-b.

### Missing correction target and cycles

When a correction's target is never present among the group's non-correction survivors at any point in the fixpoint iteration, move the correction row itself to superseded_memories; it does not join temporal precedence competition. Two or more corrections that only target one another's resulting memory_ids form a cycle: none of their targets ever becomes present, so every correction in the cycle is superseded and any untouched base memory in that group competes normally.

## Temporal precedence

Among all candidates remaining after correction targeting within a group, select the winner using conflict_mode from the policy loaded during ingest. closed mode selects highest anchor_ms; open mode selects highest confidence. Tie-breakers for each mode are documented in retention-policy.md.

conflict_mode is independent of export_mode. A policy may set conflict_mode closed for ingest while export_mode open governs export-time quota only.

## Profile seeding

Profile baselines enter each group before session and tool candidates. Any session or tool candidate with the same subject and predicate supersedes the profile baseline using temporal precedence rules.

## Tool versus session

Tool and session candidates participate in the same temporal precedence ordering. discovery_seq breaks no ties; it is metadata only.

## Semantic dedup pass

After each group has one provisional winner, run semantic dedup across all provisional winners per semantic-dedup.md. Losers of semantic dedup move to superseded_memories and the winner may list merged_from.
