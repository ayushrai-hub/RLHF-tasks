# Cheat Sheet — Referral-attribution

This file is reviewer-only. It describes the expected solution path and must not be exposed to the solving agent.

## Task Frame

The GitHub-style issue only states that `/app/output/report.json` regressed against the RF rollout tickets around sign-in referrals, cross-referrer attribution, and invalid self-attribution. It does not restate any acceptance rules. A correct solving agent must fetch the linked Jira tickets and the referral PRD page through the local context API, then repair `apply_referral_events` in `/app/referral_processor.py` and regenerate the report via `python3 /app/reconcile.py`.

The reduced slice ships with a broken `apply_referral_events` that (1) ignores `signin` events, (2) dedupes referees with a single global `seen_referred_users` set, and (3) has no self-referral guard.

## Expected Reasoning

- Fetch `PPL-702` to establish that attribution must be deterministic and that only known referral codes move progress.
- Fetch `PPL-798` (RF-020) to learn that `eventType=signin` is eligible referral activity, not just first-time `signup`.
- Fetch `PPL-802` (RF-022) to learn that the same referee can credit two different referrers; idempotency must be scoped to the same referrer/referee pair, not a global referred-user set.
- Fetch `PPL-804` (RF-023) and `PPL-806` (RF-024) to learn that self-referral is invalid: ignore any event where `referredUserId` equals the referrer's `userId`, regardless of device.
- Fetch PRD page `1929576453` to confirm the consolidated rules and the deterministic output shape (rows sorted by `userId`, each `referredUsers` list sorted).

## Correct Fix Shape

Rewrite `apply_referral_events` so that, per event with a known `referralCode`:

- Accept the event only when `eventType` is in `{"signup", "signin"}`.
- Skip events with no `referredUserId`.
- Skip the event when `referredUserId == row["userId"]` (self-referral, before any increment).
- Remove the module-level `seen_referred_users` global set. Dedupe per-referrer: only append `referredUserId` and increment `referralCount` if it is not already in that referrer's own `referredUsers` list.

`build_report` keeps the deterministic output written to `/app/output/report.json`: rows sorted by `userId`, each record `{userId, referralCount, referredUsers}` with `referredUsers` sorted. Running `python3 /app/reconcile.py` produces the report from `data/referrers.json` and `data/events.json`.

For the bundled stream this yields `u-alice` = count 2 with `["u-yuki", "u-zoe"]` (signin from `u-zoe`, two idempotent signups from `u-yuki`, self-signup from `u-alice` dropped) and `u-bob` = count 1 with `["u-zoe"]` (same referee crediting a second referrer).

## Hidden Verifier Focus

`tests/test_outputs.py` asserts: the report exists; `u-alice` counts the `signin` referral of `u-zoe`; `u-bob` independently credits `u-zoe` (`{count 1, ["u-zoe"]}`); `u-alice` never appears in its own `referredUsers` (self-referral dropped); `u-alice` equals `{count 2, ["u-yuki", "u-zoe"]}` (pair-scoped idempotency on the duplicate `u-yuki` signup). A final test calls `build_report` directly on synthetic referrers/events to confirm pair-scoped (not global) idempotency: a shared referee credits both `u-first` and `u-second` once each, `purchase` events are ignored, and self-referral is dropped.

## Common Failure Modes

- Keeping the `signup`-only filter, dropping the `signin` referral of `u-zoe`.
- Keeping the global `seen_referred_users` set, so `u-zoe` credits only the first referrer and `u-bob` stays at count 0.
- Omitting the self-referral guard, so `u-alice` credits itself.
- Counting duplicate same-pair events twice (incrementing without the `referredUsers` membership check).
- Counting non-referral event types (e.g. `purchase`) or breaking deterministic sorting of rows / `referredUsers`.
