<!-- harbor_instruction_version: 1 -->
# YouTube live-chat nudge scheduler ignores the experiment timing window

The reduced nudge scheduler in `/app` no longer matches the experiment timing rules. Messages are being sent too frequently and the plan does not honor the post-poll grace window from the linked experiment doc. Fix the implementation so `python3 /app/reconcile.py` writes the correct deterministic `/app/output/report.json` for the bundled timeline fixtures.

Linked internal context from the original work: PPL-1087, PPL-1189, experiment-youtube-live-chat-nudge-bot. Fetch linked context only through the local API: use `curl -s http://127.0.0.1:8765/rest/api/3/issue/<key>` for Jira-style tickets and `curl -s http://127.0.0.1:8765/wiki/rest/api/content/<id>` for design-doc pages. Public smoke tests may be available in `/tests`, but final grading uses hidden verifier tests.
