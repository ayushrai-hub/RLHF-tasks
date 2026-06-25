# Task Capabilities: Referral Attribution

## Benchmark Purpose

This task tests whether a coding agent can repair a small referral-attribution computation by reconstructing the acceptance rules from linked internal context rather than from the issue text. The issue only names the regression areas (sign-in referrals, cross-referrer credit, self-attribution); the actual rules live in the linked tickets and PRD.

## Context Retrieval

The issue links Jira tickets PPL-702, PPL-798, PPL-802, PPL-804, PPL-806 and PRD page 1929576453, fetchable only through the local Jira/Confluence API emulator at `http://127.0.0.1:8765`. The `jira.jsonl` and `docs/` files are backing data for that emulator, not the intended interface. The task is only properly specified once those IDs are retrieved.

## Cross-Document Inference

Correct behavior requires combining several rules: signin counts as eligible activity (PPL-798), idempotency is pair-scoped so one referee can credit two referrers (PPL-802), self-referral is invalid across devices (PPL-804/PPL-806), and only known codes move deterministic progress (PPL-702, PRD). No single document is sufficient; the bug surface spans all of them.

## Coding Judgment

The fix is a focused rewrite of `apply_referral_events` in `referral_processor.py`: widen the event filter to `{signup, signin}`, replace the global `seen_referred_users` set with per-referrer membership dedup, and add a `referredUserId == userId` self-referral guard before incrementing `referralCount`. Determinism (rows sorted by `userId`, each `referredUsers` sorted) must be preserved.

## Hidden Evaluation

The private tests in `tests/test_outputs.py` check the bundled report (signin credit, independent cross-referrer credit, self-referral exclusion, same-pair idempotency for `u-alice` = `{2, [u-yuki, u-zoe]}`) plus a synthetic `build_report` case proving pair-scoped idempotency and that non-referral events like `purchase` are ignored. Passing the public smoke test alone is not sufficient evidence the task is solved.

## Review Signal

Useful run logs should show API calls for the linked Jira/PRD IDs before or during the fix, indicating the agent recovered the rules rather than guessing. The authoritative grade still comes from the hidden verifier, not from the presence of those calls.
