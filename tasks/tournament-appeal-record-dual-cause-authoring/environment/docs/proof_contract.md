# Rookline proof contract

The public workflow writes `/app/output/tournament-appeal-proof.json`. The document schema is `rookline.tournament-appeal-proof.v1` and `generated_by` is `rookline prove`. The source fingerprint is the deterministic FNV-1a 64-bit fingerprint of the case file bytes, rendered as `fnv1a64:<16 lowercase hex digits>`.

Each case entry contains a judge object, match records, appeal records, and standings. Match status is `accepted`, `rejected`, `replay_accepted`, or `replay_rejected`. Rejected records preserve the reason strings in their match errors and do not produce a winner. Appeal records report the replay status of their target match. Standings are sorted by points descending, wins descending, then player id ascending, with wins worth three points and draws worth one point for each player.

The proof is a regenerated artifact. Changing the proof without rerunning the workflow does not establish the contract because the proof must remain tied to the local case records and rule authority.
