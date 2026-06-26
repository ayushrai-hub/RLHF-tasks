# Task Capabilities: YouTube Nudge Scheduler

## Benchmark Purpose

This task tests whether the agent can translate a product experiment doc into deterministic scheduling logic.

## Context Retrieval

The issue mentions only the scheduler symptom and linked context IDs. The exact timing window and rotation behavior must be fetched through the local Jira/Confluence API emulator.

## Cross-Document Inference

The task requires connecting the experiment description to the backend service ticket. The code change is small, but the behavior depends on timing semantics spread across the linked context.

## Coding Judgment

The implementation must preserve deterministic output while handling active poll windows, grace-window extension, minimum send spacing, and cyclic message rotation.

## Hidden Evaluation

Hidden tests check the full timeline and message ordering, not just whether any output file exists. Public tests should be treated as smoke coverage only.

## Review Signal

Good run logs should show API calls for `PPL-1087`, `PPL-1189`, and `experiment-youtube-live-chat-nudge-bot` before or during the code change.
