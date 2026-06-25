<!-- harbor_instruction_version: 1 -->
# Referral attribution regressed against the RF rollout tickets

The reduced referral attribution slice in `/app` no longer matches the RF rollout acceptance tickets. The generated `/app/output/report.json` is wrong for the bundled event stream, especially around sign-in referrals, cross-referrer attribution, and invalid self-attribution cases.

Fix the implementation so `python3 /app/reconcile.py` writes the correct deterministic report. The original GitHub issue did not restate the acceptance rules; it linked the internal RF tickets and PRD page below.

Linked internal context from the original work: PPL-702, PPL-798, PPL-802, PPL-804, PPL-806, 1929576453. Fetch linked context only through the local API: use `curl -s http://127.0.0.1:8765/rest/api/3/issue/<key>` for Jira-style tickets and `curl -s http://127.0.0.1:8765/wiki/rest/api/content/<id>` for design-doc pages. Public smoke tests may be available in `/tests`, but final grading uses hidden verifier tests.
