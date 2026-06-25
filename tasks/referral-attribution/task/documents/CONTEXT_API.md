# Context API — referral-attribution

In the live task the agent does **not** read these files directly. The linked
Jira tickets and Confluence pages are fetched at solve time through a local
offline API emulator. The raw bundle is included here only so reviewers can
see the context that backs the API.

## Endpoints

- Jira issue:  `curl -s http://127.0.0.1:8765/rest/api/3/issue/{id}`
- Jira search: `curl -s http://127.0.0.1:8765/rest/api/3/search`
- Confluence:  `curl -s http://127.0.0.1:8765/wiki/rest/api/content/{id}`

## Linked Jira tickets

- `PPL-702` — BE - Invite Friends - Refer and Earn (`/rest/api/3/issue/PPL-702`)
- `PPL-798` — [RF-020] Referral counted on existing user sign-in via link (`/rest/api/3/issue/PPL-798`)
- `PPL-802` — [RF-022] Referee from two referrers credits both (`/rest/api/3/issue/PPL-802`)
- `PPL-804` — [RF-023] Self-referral on same device not counted (`/rest/api/3/issue/PPL-804`)
- `PPL-806` — [RF-024] Self-referral on different device not counted (`/rest/api/3/issue/PPL-806`)

## Linked Confluence pages

- `1929576453` — Refer Friends inside Pi Lens (Hard referral) (`/wiki/rest/api/content/1929576453`)
