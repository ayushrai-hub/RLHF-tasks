<!-- harbor_instruction_version: 1 -->
# Backend hard-referral lock state still trips after unlock

The reduced Pi Lens backend slice in `/app` is reproducing a regression from the hard-referral rollout. Users who hit the referral quota can still stay locked, and threshold boundaries do not match the rollout rules from the linked backend work. Fix the implementation so `python3 /app/reconcile.py` writes the correct deterministic `/app/output/report.json` for the bundled fixture data.

Linked internal context from the original work: PPL-702, PPL-997, PPL-1000, PPL-1009, PPL-1011, 1929576453. Fetch linked context only through the local API: use `curl -s http://127.0.0.1:8765/rest/api/3/issue/<key>` for Jira-style tickets and `curl -s http://127.0.0.1:8765/wiki/rest/api/content/<id>` for design-doc pages. Public smoke tests may be available in `/tests`, but final grading uses hidden verifier tests.
