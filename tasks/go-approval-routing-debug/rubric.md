# Rubric — go-approval-routing-debug

Single flat rubric. Paste each line into the submission UI rubric box (one
entry per line). Positive points total 40 (within the 10–40 range); the four
negatives describe undesirable behaviour.

```
Agent reads the handlers, store and models to learn the existing routing and JSON request/response shapes before editing, +2
Agent satisfies a stage only when at least `required` distinct eligible approvers have approved it (a true quorum, not one approver counted twice), and opens the next stage only then, +4
Agent treats the first not-yet-satisfied stage as the current stage and accepts decisions only for that stage, marking the request approved once every stage is satisfied, +3
Agent makes a reject at the current stage reject the whole request immediately and terminal, and refuses any further decision once a request is approved, rejected or canceled, +3
Agent makes revoke withdraw the approver's most recent active decision and, when that drops an earlier satisfied stage below quorum, rolls the request back to that stage and discards every decision recorded for later stages so it cannot vault forward on stale approvals, +4
Agent makes editing a request discard all recorded decisions, reset it to the first stage, and bump a content `revision` counter that is separate from the optimistic-concurrency `version`, +3
Agent computes a stage's effective eligible set as the literal `eligible` ids unioned with the live current members of every referenced group, resolved on read so a group membership edit immediately re-routes referencing requests and their cached view never goes stale, +4
Agent rejects a stage referencing an unknown group with 422, refuses to delete a group still referenced by any request with 409, takes an If-Match on group edits (428 missing / 412 stale) bumping the group version, and reports a lifetime groups-created count that survives deletion, +3
Agent validates create (non-empty title and author, at least one stage, each stage named with `required` >= 1, a non-empty effective eligible set, and `required` no larger than the distinct effective-eligible count) and the group create (non-empty name, at least one member), returning 422 on violation, +3
Agent rejects an ineligible approver (422), a second decision from someone who already decided the current stage (409), and a decision other than approve or reject (422), +2
Agent paginates 1-based (default page size 20) so page 1 starts at the first record and consecutive pages never overlap, reports `total` as the full match count, serializes an empty result as a JSON array not null, and honors the status filter and sort option, +3
Agent makes /approvers/{id} report currently-active approvals versus a lifetime approval count that never drops on revoke or request deletion, plus the requests currently waiting on that approver at their current stage, +3
Agent makes /stats report lifetime requests created (surviving deletion), currently-active request count, lifetime approvals recorded, and lifetime revokes processed, +2
Agent enforces If-Match on edit, cancel and revoke (428 missing / 412 stale) returning the version in an ETag, requires application/json (415) with no unknown fields (400), and returns 405 with an Allow header on wrong methods, +1
Agent edits source files without first reading them, altering the JSON request/response contract the handlers and store already define, -3
Agent leaves the service in a non-compiling or non-bootable state (go build -race fails or the server does not start), -5
Agent modifies the test files or the reference solution instead of fixing the application source under /app/src, -5
Agent ships code with an unresolved data race that aborts under the race detector, -4
```
