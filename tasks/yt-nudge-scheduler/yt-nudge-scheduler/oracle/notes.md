# Oracle Notes: YouTube Nudge Scheduler

This file is reviewer-only and should not be mounted into the solving agent workspace.

## Task Frame

The issue describes a reduced YouTube live-chat nudge scheduler that is violating experiment timing rules. The linked Jira tickets and experiment design doc contain the actual timing contract.

## Expected Reasoning

- Use `PPL-1087` to identify the experiment scope and nudge behavior.
- Use `PPL-1189` to identify the backend service context.
- Use the design doc `experiment-youtube-live-chat-nudge-bot` for the exact scheduler rules.

## Correct Fix Shape

The scheduler should scan candidate ticks and emit messages only while a poll is active or within the configured post-poll grace window.

Messages must be spaced by at least the configured minimum interval. With the bundled config, that means no two sends should be less than ten seconds apart.

The message bank should rotate deterministically in sequence and wrap around when exhausted.

## Hidden Verifier Focus

The private verifier checks the complete send timeline, the post-poll grace window, the absence of sends outside the window, and message rotation order.

## Common Failure Modes

- Stopping exactly at poll end instead of allowing the grace window.
- Treating the grace window as a new independent schedule that resets spacing.
- Sending at every candidate tick without enforcing minimum spacing.
- Randomizing or sorting message text instead of rotating through the bank.
