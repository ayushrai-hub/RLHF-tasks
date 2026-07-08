# Architecture

## Overview

The interval tree calendar service indexes time-bounded events using an augmented Binary Search Tree (BST) keyed by `start_ms`, with each node storing a `max_end_ms` field representing the maximum `end_ms` among the node and all its descendants.

## Augmented Interval Tree

Events are stored in a BST where the key is `start_ms`. Each node additionally tracks `max_end_ms = max(end_ms, left.max_end_ms, right.max_end_ms)`. This augmentation enables efficient stabbing queries: when searching for all events containing time T, any subtree whose root has `max_end_ms < T` can be pruned because no descendant can contain T either.

The BST links (`tree_left_id`, `tree_right_id`, `tree_parent_id`) are stored in SQLite alongside event data. No in-memory tree is maintained; all tree operations read and write the database directly.

## HTTP Layer

busybox httpd serves from `/app/www/` on port 8080. The `httpd.conf` uses an `E404` handler so every request that does not match a static file is routed to `calendar.tcl`. The Tcl script reads standard CGI environment variables (`REQUEST_METHOD`, `REQUEST_URI`, `QUERY_STRING`, `CONTENT_LENGTH`) and writes a complete HTTP response (status line + headers + body) to stdout.

## Stabbing Query

A stabbing query at time T walks the BST from the root. At each node:
1. Prune the left subtree if `left.max_end_ms < T`.
2. Prune the right subtree if `right.max_end_ms < T`.
3. Include the current node if `start_ms <= T <= end_ms`.

## Deletion and Propagation

When an event is deleted the BST is restructured via standard BST deletion (replace with in-order successor or predecessor). After restructuring, `max_end_ms` is recalculated bottom-up along the ancestor path to the root so the augmentation invariant is maintained.

## Persistence

All state lives in `/app/data/calendar.db` (SQLite). The query log (`/app/data/query_log.ndjson`) appends one NDJSON line per `/stab` query, capturing `{query_type, param_ms, result_count, duration_us, ts_ms}`.
