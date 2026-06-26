# Context API — yt-nudge-scheduler

In the live task the agent does **not** read these files directly. The linked
Jira tickets and Confluence pages are fetched at solve time through a local
offline API emulator. The raw bundle is included here only so reviewers can
see the context that backs the API.

## Endpoints

- Jira issue:  `curl -s http://127.0.0.1:8765/rest/api/3/issue/{id}`
- Jira search: `curl -s http://127.0.0.1:8765/rest/api/3/search`
- Confluence:  `curl -s http://127.0.0.1:8765/wiki/rest/api/content/{id}`

## Linked Jira tickets

- `PPL-1087` — YouTube Live Chat Bot experiment context. (`/rest/api/3/issue/PPL-1087`)
- `PPL-1189` — Backend YouTube chat bot implementation context. (`/rest/api/3/issue/PPL-1189`)

## Linked Confluence pages

- `experiment-youtube-live-chat-nudge-bot` — Experiment scheduler timing and message rotation rules. (`/wiki/rest/api/content/experiment-youtube-live-chat-nudge-bot`)
