# Interval Tree Calendar Service — SPEC

## §1 Process Model

The service listens for HTTP requests on the configured port. The startup and shutdown contract is:

1. `bash /app/scripts/start_service.sh` calls `init_db.sh` to create the SQLite database if it does not exist, then launches the service (in the background via `nohup`) with its PID written to `/app/run/server.pid`.
2. The service answers every endpoint in §4 on `BIND_PORT`.
3. The service can be stopped by sending SIGTERM to the PID or by running `bash /app/scripts/stop_service.sh`.

The service is a standalone Tcl 8.6 TCP server at `/app/src/calendar_server.tcl`. It sources `/app/src/analytics.tcl` at startup, which must define the twenty analytics procedures documented in §14. All other endpoints (event CRUD, stab, overlap, stats) are pre-built in the server and require no changes.

## §2 Configuration

| Variable       | Default                  | Description                        |
|----------------|--------------------------|------------------------------------|
| `BIND_PORT`    | `8080`                   | TCP port for the HTTP server       |
| `CALENDAR_DB`  | `/app/data/calendar.db`  | Path to the SQLite database file   |

## §3 Database Schema

```sql
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    max_end_ms INTEGER NOT NULL,
    tree_left_id INTEGER REFERENCES events(id),
    tree_right_id INTEGER REFERENCES events(id),
    tree_parent_id INTEGER REFERENCES events(id),
    created_at_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS stab_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at_ms INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    duration_us INTEGER NOT NULL,
    ts_ms INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS overlap_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER NOT NULL,
    result_count INTEGER NOT NULL,
    duration_us INTEGER NOT NULL,
    ts_ms INTEGER NOT NULL
);
```

`max_end_ms` — the maximum `end_ms` of the node and all its descendants in the BST. This must be kept correct on every insert, update, and delete.

`tree_left_id`, `tree_right_id`, `tree_parent_id` — BST links stored in the database. `NULL` means no child / no parent (root).

## §4 HTTP Endpoints

### POST /events

Insert a new event.

**Request body (JSON):**
```json
{"name": "string", "start_ms": 1000, "end_ms": 2000, "metadata": {}}
```

**Response 201 (JSON):**
```json
{"id": 1, "name": "string", "start_ms": 1000, "end_ms": 2000, "max_end_ms": 2000}
```

**Response 400:** missing required fields (`name`, `start_ms`, `end_ms`).

### GET /events/:id

Return the event with the given id.

**Response 200 (JSON):**
```json
{"id": 1, "name": "string", "start_ms": 1000, "end_ms": 2000, "max_end_ms": 2000, "metadata": {}}
```

**Response 404:** event not found.

### PUT /events/:id

Update the `name` and/or `end_ms` of an existing event. At least one of the two fields must be provided.

**Request body (JSON):** one or both of:
```json
{"name": "new_name", "end_ms": 3000}
```

If `end_ms` changes, re-propagate `max_end_ms` through all ancestors (same walk-up algorithm as insert/delete).

**Response 200:** the updated event object (same shape as GET /events/:id).

**Response 400:** no updatable fields provided.

**Response 404:** event not found.

### GET /stab?at=<ms>

Return all events where `start_ms <= at <= end_ms`. Uses the augmented BST traversal described in §5a. Every response event includes a `metadata` field.

**Response 200 (JSON):**
```json
{"at": 1500, "events": [{"id": 1, "name": "string", "start_ms": 1000, "end_ms": 2000, "metadata": {}}]}
```

### GET /overlap?start=<ms>&end=<ms>

Return all events that overlap the interval `[start, end]`. An event overlaps if `event.start_ms <= end AND event.end_ms >= start`. Touching boundaries count as overlapping.

**This query MUST use the augmented-interval BST traversal described in §5b** (not a plain SQL scan). Every response event includes a `metadata` field. The query is logged to both `overlap_log` and `query_log.ndjson` (see §7).

**Response 200 (JSON):**
```json
{"start": 1000, "end": 2000, "events": [{"id": 1, "name": "string", "start_ms": 1000, "end_ms": 2000, "metadata": {}}]}
```

### DELETE /events/:id

Remove the event with the given id from the tree. Propagate `max_end_ms` updates to all ancestor nodes.

**Response 200 (JSON):**
```json
{"id": 1, "deleted": true}
```

**Response 404:** event not found.

### GET /stats

Return aggregate statistics.

**Response 200 (JSON):**
```json
{"total_events": 5, "tree_depth": 3, "overlapping_pairs": 4, "leaf_count": 2, "min_start_ms": 100}
```

- `total_events` — number of rows in the `events` table.
- `tree_depth` — height of the BST counted in nodes (root is level 1, so a single-node tree has tree_depth = 1; 0 if the tree is empty).
- `overlapping_pairs` — number of pairs (i, j) with i.id < j.id where `i.start_ms <= j.end_ms AND j.start_ms <= i.end_ms`. Each pair is counted once.
- `leaf_count` — number of nodes with no children (both `tree_left_id IS NULL` and `tree_right_id IS NULL`). 0 if the tree is empty.
- `min_start_ms` — the minimum `start_ms` across all events. 0 if the tree is empty.

### GET /peak?start=<ms>&end=<ms>

Report the peak concurrency: the maximum number of stored events that are simultaneously active at any single instant inside the window `[start, end]`, together with the earliest instant at which that maximum occurs. An event is *active* at instant `t` when `start_ms <= t <= end_ms`. See §8 for the exact definition and the instant-selection rule.

**Response 200 (JSON):**
```json
{"start": 1000, "end": 5000, "max_concurrency": 3, "at_ms": 2000, "peak_duration_ms": 500, "events_at_peak": [1, 3, 7]}
```

- `events_at_peak` — list of event IDs (integers) that are active at `at_ms`, sorted ascending. Empty list when `max_concurrency` is 0.
- `peak_duration_ms` — total integer instants `t` in `[start, end]` where `c(t) == max_concurrency`. Computed by a change-point sweep over all event `start_ms` and `end_ms+1` values in `(start, end]`. When `max_concurrency` is 0, `peak_duration_ms` equals `end - start + 1`.

When no event is active anywhere in the window, `max_concurrency` is `0`, `at_ms` is the window `start`, `peak_duration_ms` is `end - start + 1`, and `events_at_peak` is `[]`.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /schedule?start=<ms>&end=<ms>

Return the size of a maximum-cardinality set of pairwise non-overlapping events chosen from the events **fully contained** in the window `[start, end]` (i.e. `start_ms >= start AND end_ms <= end`). Two events overlap when `a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms` — touching boundaries count as overlapping, so two selected events must not touch. See §9 for the selection algorithm.

**Response 200 (JSON):**
```json
{"start": 1000, "end": 9000, "max_non_overlapping": 2, "covered_ms": 400, "selected_ids": [3, 5]}
```

- `selected_ids` — list of event IDs chosen by the earliest-finishing-time greedy, in the order they were selected (sorted by `end_ms` ASC, then `id` ASC for ties).
- `covered_ms` — total integer instants covered by the selected events: `sum(end_ms - start_ms + 1)` for each selected event. Since selected events are pairwise non-overlapping, no instant is double-counted.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /gaps?start=<ms>&end=<ms>

Return the free gaps inside `[start, end]`: the maximal runs of consecutive integer instants in the window during which **no** event is active. See §10 for the exact definition and merge rule.

**Response 200 (JSON):**
```json
{"start": 0, "end": 100, "gaps": [{"start_ms": 41, "end_ms": 59}]}
```

When no event overlaps the window the single gap is the whole window `[{"start_ms": start, "end_ms": end}]`; when the window is fully covered the `gaps` list is empty.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /coverage?start=<ms>&end=<ms>

Report the total number of integer time-units in `[start, end]` covered by at least one stored event. Uses the clip-and-merge algorithm from §11.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "covered_ms": 60, "free_ms": 40}
```
- `covered_ms` — number of integer instants in `[start, end]` covered by at least one event. 0 if no event intersects the window.
- `free_ms` — `(end - start + 1) - covered_ms`. Always non-negative.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /longest_gap?start=<ms>&end=<ms>

Return the single longest free gap inside `[start, end]` using the §10 gap algorithm. Among all gaps return the one with the greatest `duration_ms = end_ms - start_ms + 1`; ties go to the earliest (smallest `start_ms`). When no gap exists (window fully covered) return `null` for the `gap` field.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "gap": {"start_ms": 50, "end_ms": 99, "duration_ms": 50}}
```
or when fully covered:
```json
{"start": 0, "end": 99, "gap": null}
```

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /density?start=<ms>&end=<ms>&bucket_ms=<ms>

Partition `[start, end]` into consecutive fixed-width buckets of `bucket_ms` milliseconds each. The first bucket covers `[start, start + bucket_ms - 1]`; the last bucket covers `[last_bucket_start, end]` and may be narrower than `bucket_ms`. For each bucket compute `busy_ms` — the number of integer instants in that bucket covered by at least one event — using the same clip-and-merge algorithm as §11 restricted to the bucket's range. Return buckets in ascending order.

**Response 200 (JSON):**
```json
{"start": 0, "end": 29, "bucket_ms": 10, "buckets": [
  {"bucket_start": 0, "bucket_end": 9, "busy_ms": 5},
  {"bucket_start": 10, "bucket_end": 19, "busy_ms": 5},
  {"bucket_start": 20, "bucket_end": 29, "busy_ms": 0}
]}
```

**Response 400:** missing/non-integer `start`, `end`, or `bucket_ms`; `start > end`; or `bucket_ms < 1`.

### GET /timeline?start=<ms>&end=<ms>&resolution_ms=<ms>

Partition `[start, end]` into consecutive slots of `resolution_ms` milliseconds each (same bucketing rule as §13: last slot may be narrower). For each slot `[ss, se]`, compute the peak concurrency using the §8 algorithm restricted to `[ss, se]`: evaluate `c(t)` at the candidate set `{ss} ∪ { e.start_ms : ss < e.start_ms <= se }` and take the maximum.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "resolution_ms": 25, "slots": [
  {"slot_start": 0, "slot_end": 24, "peak_concurrency": 2},
  {"slot_start": 25, "slot_end": 49, "peak_concurrency": 1},
  {"slot_start": 50, "slot_end": 74, "peak_concurrency": 0},
  {"slot_start": 75, "slot_end": 99, "peak_concurrency": 1}
]}
```

**Response 400:** missing/non-integer `start`, `end`, or `resolution_ms`; `start > end`; or `resolution_ms < 1`.

### GET /conflicts?start=<ms>&end=<ms>&threshold=<int>

Return all events whose interval intersects `[start, end]` AND that are active at some instant `t` in `[max(event.start_ms, start), min(event.end_ms, end)]` where `c(t) > threshold`. Use the same candidate-instant sweep as §8 (restricted to events intersecting the window). Sorted by `start_ms` ASC, then `id` ASC. `threshold` must be >= 0.

**Response 200 (JSON):**
```json
{"start": 1000, "end": 5000, "threshold": 1,
 "conflicting_events": [
   {"id": 1, "name": "A", "start_ms": 1000, "end_ms": 3000},
   {"id": 2, "name": "B", "start_ms": 2000, "end_ms": 4000}
 ]}
```

When no instant in the window has `c(t) > threshold`, `conflicting_events` is `[]`.

**Response 400:** missing/non-integer params; `start > end`; or `threshold < 0`.

See §17–§20 for the detailed algorithm descriptions of the four endpoints below.

### GET /heatmap?start=<ms>&end=<ms>&resolution_ms=<ms>

See §17. **Response 400:** missing/non-integer params; `start > end`; or `resolution_ms < 1`.

### GET /merge?start=<ms>&end=<ms>

See §18. **Response 400:** missing/non-integer params; `start > end`.

### GET /event_concurrency?start=<ms>&end=<ms>

See §19. **Response 400:** missing/non-integer params; `start > end`.

### GET /free_slots?start=<ms>&end=<ms>&min_duration_ms=<ms>

See §20. **Response 400:** missing/non-integer params; `start > end`; or `min_duration_ms < 1`.

### GET /weighted_schedule?start=<ms>&end=<ms>

Among events **fully contained** in `[start, end]` (`start_ms >= start AND end_ms <= end`), find the maximum-total-weight subset such that no two selected events overlap. Overlap is the §6 relation — two selected events must satisfy `later.start_ms > earlier.end_ms` (touching is not allowed). The weight of an event is the value of `metadata_json["weight"]` parsed as a float; if the key is absent, non-numeric, or the metadata is not a parseable JSON object, the weight defaults to `1.0`. See §21 for the exact DP algorithm.

**Response 200 (JSON):**
```json
{"start": 1000, "end": 9000, "max_weight": 7.50, "selected_ids": [3, 5], "covered_ms": 400}
```
- `max_weight` — maximum total weight of the selected subset, formatted to exactly 2 decimal places.
- `selected_ids` — IDs of selected events in `end_ms ASC, id ASC` order (the order in which the DP traceback produces them).
- `covered_ms` — sum of `(end_ms - start_ms + 1)` for each selected event.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /coloring?start=<ms>&end=<ms>

Assign each event intersecting `[start, end]` a non-negative integer "color" such that no two overlapping events share a color, using the **minimum** number of distinct colors. Two events overlap when `a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms`. The minimum number of colors required equals the peak concurrency of events intersecting the window. See §22 for the exact greedy algorithm.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "num_colors": 3, "assignments": [
  {"id": 1, "color": 0},
  {"id": 2, "color": 1},
  {"id": 3, "color": 2}
]}
```
- `num_colors` — number of distinct colors used (0 if no events intersect the window).
- `assignments` — list sorted by `color ASC`, then `id ASC`.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /concurrency_runs?start=<ms>&end=<ms>

See §23. **Response 400:** missing/non-integer params; `start > end`.

### GET /interval_cover?start=<ms>&end=<ms>&target_ms=<ms>

See §24. **Response 400:** missing/non-integer params; `start > end`; or `target_ms < 1`.

### GET /earliest_available?after=<ms>&duration_ms=<ms>

See §25. **Response 400:** missing/non-integer params; or `duration_ms < 1`.

### GET /room_schedule?start=<ms>&end=<ms>&rooms=<int>

See §26. **Response 400:** missing/non-integer params; `start > end`; or `rooms < 1`.

### GET /overlap_components?start=<ms>&end=<ms>

See §27. **Response 400:** missing/non-integer params; or `start > end`.

### GET /healthz

**Response 200 (JSON):**
```json
{"status": "ok"}
```

## §5a Augmented Interval Tree — Stabbing Query

The BST is keyed by `start_ms`. For equal `start_ms`, the newer event goes right. Each node's `max_end_ms` satisfies:

```
max_end_ms = max(end_ms, left.max_end_ms or 0, right.max_end_ms or 0)
```

**Insertion:** walk from root; go left if `start_ms < node.start_ms`, else right. Set the inserted node's `max_end_ms = end_ms`. Walk back up to root updating `max_end_ms` at each ancestor.

**Stabbing query at T:** traverse from root using a stack. At each node, include it if `start_ms <= T <= end_ms`. Push the left child only if it exists and `left.max_end_ms >= T`. Push the right child only if it exists and `right.max_end_ms >= T`.

## §5b Augmented Interval Tree — Overlap Query

The overlap query for range `[Q_start, Q_end]` also uses the BST, exploiting `max_end_ms` and the BST ordering property to prune:

**Overlap traversal from root using a stack:**

For each visited node:
1. If `node.start_ms <= Q_end AND node.end_ms >= Q_start`, include the node in results.
2. **Left subtree pruning:** push the left child only if it exists and `left.max_end_ms >= Q_start`. If `left.max_end_ms < Q_start`, no event in the left subtree can end at or after `Q_start`, so the entire left subtree is skipped.
3. **Right subtree pruning:** push the right child only if it exists and `node.start_ms <= Q_end`. By the BST ordering property, all right descendants have `start_ms >= node.start_ms`. If `node.start_ms > Q_end`, every right descendant also starts after `Q_end` and cannot overlap, so the right subtree is skipped.

A plain SQL scan (`WHERE start_ms <= Q_end AND end_ms >= Q_start`) does not use these pruning rules and is **not acceptable** for this endpoint.

## §6 Overlap Counting

`overlapping_pairs` in `/stats` counts pairs (i, j) where i.id < j.id and the intervals overlap:

```
i.start_ms <= j.end_ms AND j.start_ms <= i.end_ms
```

This is computed over all current events in the database. Each pair is counted exactly once.

## §7 Query Log

Every `/stab` query appends one line to `/app/data/query_log.ndjson`:

```json
{"query_type": "stab", "param_ms": 1500, "result_count": 3, "duration_us": 412, "ts_ms": 1719000000000}
```

Every `/overlap` query appends one line to `/app/data/query_log.ndjson` **and** inserts one row into `overlap_log`:

```json
{"query_type": "overlap", "param_start_ms": 1000, "param_end_ms": 2000, "result_count": 3, "duration_us": 412, "ts_ms": 1719000000000}
```

Fields:
- `query_type` — `"stab"` for stab queries, `"overlap"` for overlap queries.
- `param_ms` — the `at` parameter (stab only).
- `param_start_ms`, `param_end_ms` — the `start` and `end` parameters (overlap only).
- `result_count` — number of events returned.
- `duration_us` — query duration in microseconds.
- `ts_ms` — wall-clock timestamp in milliseconds when the query completed.

## §8 Peak Concurrency (`GET /peak`)

Define `c(t)` = the number of stored events with `start_ms <= t <= end_ms`. The endpoint reports, over integer instants `t` in `[start, end]`:

- `max_concurrency` = `max` of `c(t)` for `t` in `[start, end]`.
- `at_ms` = the **smallest** `t` in `[start, end]` at which `c(t) == max_concurrency`.
- `events_at_peak` = the list of event IDs active at `at_ms`, sorted ascending.

`c(t)` is a step function that only ever increases at an event's `start_ms`, so the maximum over the window is attained either at the window `start` or at some event's `start_ms` lying in `(start, end]`. It is therefore sufficient to evaluate `c(t)` at the candidate set `{start} ∪ { e.start_ms : start < e.start_ms <= end }` and take the maximum, breaking ties toward the smallest `t`. Events whose interval began before the window but is still active at `start` are counted at `t = start`. When the window contains no active instant, `max_concurrency = 0`, `at_ms = start`, and `events_at_peak = []`.

The `peak_concurrency` procedure returns a list `{max_concurrency at_ms peak_duration_ms id1 id2 ...}` — the first three elements are `max_concurrency`, `at_ms`, and `peak_duration_ms`, followed by the event IDs active at `at_ms` sorted ascending.

## §9 Maximum Non-Overlapping Set (`GET /schedule`)

Among the events **fully contained** in `[start, end]` (`start_ms >= start AND end_ms <= end`), return the maximum number that can be chosen so that no two of them overlap. Overlap is the §6 relation (`a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms`), so two chosen events must satisfy `later.start_ms > earlier.end_ms` (strictly — touching is not allowed).

The optimum is obtained by the earliest-finishing-time greedy: sort the contained events by `end_ms` ascending (ties by `start_ms` ascending), scan once keeping the finish time of the last selected event, and select the next event only when its `start_ms` is strictly greater than that finish time. A greedy keyed on `start_ms` (or on interval length) is **not** optimal and will report the wrong count on instances containing a long event that starts early.

## §10 Free Gaps (`GET /gaps`)

An instant `t` in `[start, end]` is *busy* when some event has `start_ms <= t <= end_ms`, and *free* otherwise. A **gap** is a maximal run of consecutive free integer instants; each gap is reported as `{"start_ms": g0, "end_ms": g1}` where `g0`/`g1` are its first/last free instant, and the `gaps` list is sorted ascending.

To compute the gaps: take every event that intersects the window (`start_ms <= end AND end_ms >= start`), clip each to `[max(start_ms, start), min(end_ms, end)]`, sort by clipped start, and merge intervals that overlap **or are integer-adjacent** (the next interval's start is `<= previous end + 1`, since no free integer instant lies between them). The gaps are the portions of `[start, end]` not covered by the merged busy intervals: before the first busy interval, between consecutive merged intervals, and after the last one. If no event intersects the window, the whole window is one gap.

## §11 Coverage Algorithm (`GET /coverage`)

Take every event that intersects the window (`start_ms <= end AND end_ms >= start`), clip each to `[max(start_ms, start), min(end_ms, end)]`, sort by clipped start, and merge overlapping intervals (merge when the next interval's start is `<= previous end`; note this is strict overlap, not integer-adjacency). Sum `(end - start + 1)` over the merged intervals. Overlapping events must **not** double-count shared instants.

## §12 Longest Gap Algorithm (`GET /longest_gap`)

Compute the gaps using the §10 algorithm (with integer-adjacency merging). Among all returned gaps, find the one with the maximum `(end_ms - start_ms + 1)`. On a tie in duration, return the gap with the smallest `start_ms`. If no gap exists (empty gap list), return `null`.

## §13 Density Algorithm (`GET /density`)

Iterate over consecutive buckets of width `bucket_ms` starting at `start`. For each bucket `[bs, be]` (where `be = min(bs + bucket_ms - 1, end)`), compute `busy_ms` using the §11 coverage algorithm restricted to events intersecting `[bs, be]`. Events partially overlapping the bucket boundary must be clipped to `[bs, be]` before counting. Do not double-count overlapping events within a bucket.

## §14 Analytics Module (`/app/src/analytics.tcl`)

The HTTP server sources `/app/src/analytics.tcl` at startup and calls the following procedures for the analytics endpoints. All procedures run in the server's Tcl interpreter and may call `dbq`, `dbr`, and `dbe` (defined in `calendar_server.tcl`).

| Procedure | Called by | Returns |
|-----------|-----------|---------|
| `read_events_se` | `peak_concurrency`, `compute_timeline` | Tcl list of `{id start_ms end_ms}` triples for every row in `events` |
| `peak_concurrency S E` | `GET /peak` | List `{max_concurrency at_ms peak_duration_ms id1 id2 ...}` — first three per §8, then event IDs active at `at_ms` sorted ascending |
| `max_non_overlapping S E` | `GET /schedule` | List `{count covered_ms id1 id2 ...}` — count and covered_ms per §9, then selected event IDs sorted end_ms ASC then id ASC |
| `compute_gaps S E` | `GET /gaps`, `longest_gap_in`, `free_slots_min` | Tcl list of `{start_ms end_ms}` gap pairs per §10 |
| `compute_coverage S E` | `GET /coverage`, `compute_density` | Integer `covered_ms` per §11 |
| `longest_gap_in S E` | `GET /longest_gap` | `{start_ms end_ms}` of longest gap, or empty list `{}` if none per §12 |
| `compute_density S E B` | `GET /density` | Tcl list of `{bucket_start bucket_end busy_ms}` triples per §13 |
| `compute_timeline S E R` | `GET /timeline` | Tcl list of `{slot_start slot_end peak_concurrency}` triples per §15 |
| `find_conflicts S E T` | `GET /conflicts` | Tcl list of `{id name start_ms end_ms}` tuples per §16, sorted `start_ms ASC, id ASC` |
| `compute_heatmap S E R` | `GET /heatmap` | Tcl list of `{slot_start slot_end histogram_list mean_concurrency}` per §17 |
| `compute_merged S E` | `GET /merge` | Tcl list of `{start_ms end_ms}` merged busy intervals per §18 |
| `event_concurrency S E` | `GET /event_concurrency` | Tcl list of `{id name start_ms end_ms max_depth}` per §19, sorted max_depth DESC, start_ms ASC, id ASC |
| `free_slots_min S E M` | `GET /free_slots` | Tcl list of `{start_ms end_ms duration_ms}` per §20, sorted duration_ms DESC, start_ms ASC |
| `weighted_schedule S E` | `GET /weighted_schedule` | List `{max_weight_str covered_ms id1 id2 ...}` per §21 — `max_weight_str` is "%.2f" formatted, then covered_ms, then selected IDs in end_ms ASC then id ASC order |
| `compute_coloring S E` | `GET /coloring` | List `{num_colors {id1 color1} {id2 color2} ...}` per §22 — num_colors followed by id/color pairs sorted color ASC then id ASC |
| `compute_concurrency_runs S E` | `GET /concurrency_runs` | List of `{start_ms end_ms concurrency}` triples per §23 — maximal constant-concurrency runs, merged and sorted start_ms ASC |
| `interval_cover S E T` | `GET /interval_cover` | List `{min_events_or_null ids achieved_coverage}` per §24 — greedy minimum cardinality cover; "null" string when unreachable |
| `earliest_available A D` | `GET /earliest_available` | List `{slot_start slot_end}` per §25 — earliest free slot of duration D starting at or after A |
| `room_schedule S E R` | `GET /room_schedule` | List `{max_scheduled {id1 room1} {id2 room2} ...}` per §26 — R-machine interval partitioning maximizing scheduled count, pairs sorted id ASC |
| `overlap_components S E` | `GET /overlap_components` | List of `{min_start_ms max_end_ms id1 id2 ...}` triples-plus-ids per §27 — connected components of the overlap graph, sorted min_start_ms ASC |

If any procedure raises an error (e.g. the stub implementation), the server returns `501 Not Implemented` for that endpoint. All other endpoints (event CRUD, `/stab`, `/overlap`, `/stats`, `/healthz`) are pre-built and always functional.

## §15 Timeline Algorithm (`GET /timeline`)

For each slot `[bs, be]` of width `resolution_ms` (last slot may be narrower), compute the peak concurrency using the §8 candidate-instant sweep restricted to `[bs, be]`. Events active at `bs` but starting before `bs` are counted at `t = bs`. When the slot contains no active event, `peak_concurrency` is `0`.

## §16 Conflict Detection Algorithm (`GET /conflicts`)

Using the candidate-instant set `{start} ∪ { e.start_ms : start < e.start_ms <= end }`, compute `c(t)` for each candidate. Collect the set of conflict instants where `c(t) > threshold`. An event is included in the result if it is active at any conflict instant within its clipped range `[max(event.start_ms, start), min(event.end_ms, end)]`. When `threshold = 0`, every event intersecting the window qualifies (since `c(t) >= 1 > 0` at every instant where it's active).

### GET /heatmap?start=<ms>&end=<ms>&resolution_ms=<ms>

Partition `[start, end]` into consecutive slots of `resolution_ms` milliseconds each (same bucketing rule as §13: last slot may be narrower). For each slot `[ss, se]`, compute the full **concurrency histogram**: a zero-indexed array where element `k` is the number of integer instants in `[ss, se]` where exactly `k` events are simultaneously active. See §17 for the exact algorithm.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "resolution_ms": 25, "slots": [
  {"slot_start": 0, "slot_end": 24, "histogram": [5, 10, 10], "mean_concurrency": 1.200000},
  {"slot_start": 25, "slot_end": 49, "histogram": [5, 10, 10], "mean_concurrency": 1.200000}
]}
```

- `histogram` — JSON array of non-negative integers; `histogram[k]` is the count of instants in the slot where exactly `k` events are active. Length equals `max_level_in_slot + 1`. An all-zero-concurrency slot has `histogram = [slot_width]`.
- `mean_concurrency` — the average concurrency across the slot: `sum(k * histogram[k]) / (slot_end - slot_start + 1)`, formatted to 6 decimal places.

**Response 400:** missing/non-integer `start`, `end`, or `resolution_ms`; `start > end`; or `resolution_ms < 1`.

### GET /merge?start=<ms>&end=<ms>

Return the **interval union** of all events intersecting `[start, end]`, using the §11 strict-overlap merge algorithm (merge when `next.start <= prev.end`). Touching-but-not-overlapping events (e.g. `[0,9]` and `[10,19]`) are **not** merged.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "merged_intervals": [{"start_ms": 0, "end_ms": 39}, {"start_ms": 50, "end_ms": 69}], "covered_ms": 60}
```

- `merged_intervals` — list of merged busy intervals, each clipped to `[start, end]`, sorted by `start_ms` ascending.
- `covered_ms` — sum of `(end_ms - start_ms + 1)` over the merged intervals (equals `compute_coverage(start, end)`).

When no events intersect the window, `merged_intervals` is `[]` and `covered_ms` is `0`.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /event_concurrency?start=<ms>&end=<ms>

For each event intersecting `[start, end]`, compute the **maximum concurrency** that event experiences while active within its clipped range `[max(event.start_ms, start), min(event.end_ms, end)]`. Uses the §8 candidate-instant sweep restricted to that clipped range. Returns all such events sorted by `max_depth` descending, then `start_ms` ascending, then `id` ascending.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "events": [
  {"id": 3, "name": "C", "start_ms": 10, "end_ms": 60, "max_depth": 3},
  {"id": 1, "name": "A", "start_ms": 0,  "end_ms": 40, "max_depth": 2}
]}
```

- `max_depth` — the peak value of `c(t)` for `t` in the event's clipped range. Always `>= 1` (the event itself is active).

When no events intersect the window, `events` is `[]`.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

### GET /free_slots?start=<ms>&end=<ms>&min_duration_ms=<ms>

Return all free gaps (computed by §10) inside `[start, end]` whose `duration_ms = end_ms - start_ms + 1` is at least `min_duration_ms`, sorted by `duration_ms` descending then `start_ms` ascending.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "min_duration_ms": 10, "free_slots": [
  {"start_ms": 60, "end_ms": 79, "duration_ms": 20},
  {"start_ms": 15, "end_ms": 29, "duration_ms": 15}
]}
```

When no gap meets the minimum duration, `free_slots` is `[]`.

**Response 400:** missing/non-integer params; `start > end`; or `min_duration_ms < 1`.

## §17 Heatmap Algorithm (`GET /heatmap`)

For each slot `[bs, be]` of width `resolution_ms`:

1. Build the change-point set: `{bs}` plus every event `start_ms` in `(bs, be]` and every event `end_ms + 1` in `(bs, be]`. Add sentinel `be + 1`.
2. Sort and deduplicate the change points: `cp[0] < cp[1] < ... < cp[n]` with `cp[n] = be + 1`.
3. For each run `[cp[i], cp[i+1]-1]` (length `cp[i+1] - cp[i]`), evaluate `c(cp[i])` = number of events where `start_ms <= cp[i] <= end_ms`. Accumulate `histogram[c] += run_length`.
4. `mean_concurrency = (sum of k * histogram[k]) / (be - bs + 1)`, formatted to 6 decimal places.

The histogram array has length `max_level + 1` where `max_level` is the largest `k` with `histogram[k] > 0`. For a slot with no active events, `histogram = [be - bs + 1]` and `mean_concurrency = 0.000000`.

## §18 Merge Algorithm (`GET /merge`)

Take every event intersecting `[start, end]`, clip each to `[max(start_ms, start), min(end_ms, end)]`, sort by clipped start, and merge using strict-overlap merging (same as §11: merge when `next.start <= prev.end`). Return the merged list and its total coverage.

## §19 Event Concurrency Algorithm (`GET /event_concurrency`)

For each event `e` intersecting `[start, end]`:
1. Clip to `cs = max(e.start_ms, start)`, `ce = min(e.end_ms, end)`.
2. Build candidate set `{cs} ∪ { ev.start_ms : cs < ev.start_ms <= ce }` using ALL stored events (not just those intersecting the window).
3. Evaluate `c(t)` at each candidate; `max_depth = max c(t)`.

Sort results by `max_depth` DESC, then `start_ms` ASC (original event start, not clipped), then `id` ASC.

## §20 Free Slots Algorithm (`GET /free_slots`)

Compute the gap list using §10. Filter to gaps where `end_ms - start_ms + 1 >= min_duration_ms`. Sort by duration descending, then `start_ms` ascending. Each entry carries `duration_ms = end_ms - start_ms + 1`.

## §21 Weighted Interval Scheduling (`GET /weighted_schedule`)

Among events fully contained in `[start, end]`, find the subset with maximum total weight such that no two selected events overlap. Uses the standard weighted-interval-scheduling DP:

1. Fetch all fully-contained events sorted by `end_ms ASC`, then `id ASC`. Index them 1..n.
2. For each event `i`, compute `p(i)` = the largest index `j < i` with `events[j].end_ms < events[i].start_ms` (strict). `p(i) = 0` if no such event exists.
3. Compute `OPT[0] = 0` and for `i = 1..n`: `OPT[i] = max(OPT[i-1], weight(i) + OPT[p(i)])`.
4. Traceback: starting from `i = n`, if `weight(i) + OPT[p(i)] > OPT[i-1]` include event `i` and recurse to `p(i)`, otherwise recurse to `i-1`. Reverse the traceback list to produce the final `selected_ids` in `end_ms ASC, id ASC` order.

The weight of event `i` is `metadata_json["weight"]` as a float, defaulting to `1.0` when the key is absent or non-numeric. `max_weight` is the sum of selected weights, formatted to 2 decimal places.

## §22 Interval Graph Coloring (`GET /coloring`)

Assign each event intersecting `[start, end]` a non-negative integer color using the minimum number of colors (the minimum equals the peak concurrency). Algorithm:

1. Fetch all events intersecting `[start, end]`, sorted by `start_ms ASC`, then `id ASC`.
2. For each event `e` in that order: collect the set of colors already assigned to events `f` that were processed before `e` and overlap `e` (i.e., `f.start_ms <= e.end_ms AND f.end_ms >= e.start_ms`). Assign to `e` the smallest non-negative integer not in that set.

Return `num_colors` = number of distinct colors used, and `assignments` sorted by `color ASC`, then `id ASC`. When no events intersect the window, `num_colors = 0` and `assignments = []`.

## §23 Concurrency Runs (`GET /concurrency_runs`)

Return the run-length encoding of the concurrency function `c(t)` over `[start, end]`: a list of maximal contiguous integer ranges in which `c(t)` is constant.

Algorithm:

1. Build the change-point set: `{start}` ∪ `{e.start_ms : start < e.start_ms <= end}` ∪ `{e.end_ms + 1 : e.end_ms >= start AND e.end_ms < end}`. Add sentinel `end + 1`.
2. Sort and deduplicate the change points: `cp[0] < cp[1] < ... < cp[m]` where `cp[m] = end + 1`.
3. For each consecutive pair `[cp[i], cp[i+1]-1]`, evaluate `c(cp[i])` = number of events with `start_ms <= cp[i] <= end_ms`. Each such pair is one raw run `{cp[i], cp[i+1]-1, c}`.
4. **Merge adjacent raw runs with identical concurrency values** into a single run. This is required when touching-but-not-overlapping events produce the same change point (e.g. event A ends at T and event B starts at T+1 — both contribute to change point T+1, yielding two raw runs both with concurrency 1 that must be collapsed to one).

Return the merged list of `{start_ms, end_ms, concurrency}` triples sorted by `start_ms ASC`. When no events intersect the window, return a single run `{start, end, 0}`.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "runs": [
  {"start_ms": 0, "end_ms": 9, "concurrency": 0},
  {"start_ms": 10, "end_ms": 49, "concurrency": 1},
  {"start_ms": 50, "end_ms": 79, "concurrency": 2},
  {"start_ms": 80, "end_ms": 99, "concurrency": 1}
]}
```

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

## §24 Minimum Interval Cover (`GET /interval_cover`)

Among events intersecting `[start, end]`, find the minimum-cardinality subset whose clipped intervals form a contiguous covered range `[start, start + effective_target - 1]`, where `effective_target = min(target_ms, end - start + 1)`. If no such subset exists (an uncoverable gap blocks the frontier before reaching `start + effective_target - 1`), return `null` for `min_events`.

Algorithm (greedy interval cover):

1. Clip each intersecting event to `[max(start_ms, start), min(end_ms, end)]`.
2. Set `frontier = start - 1`, `selected = []`.
3. While `frontier < start + effective_target - 1` and events remain:
   a. Among all remaining events with `clipped_start <= frontier + 1` AND `clipped_end > frontier`, pick the one with the **largest** `clipped_end`. Ties broken by **smallest original `id`**.
   b. If no such candidate exists, break (gap is uncoverable).
   c. Advance `frontier = candidate.clipped_end`. Add the candidate to `selected`.
4. `achieved_coverage = max(0, frontier - start + 1)`.
5. If `frontier >= start + effective_target - 1`: success. Return `min_events = |selected|`, `selected_ids` sorted ascending by original `id`, and `achieved_coverage`.
6. Otherwise: return `min_events = null`, `selected_ids = []`, and `achieved_coverage`.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "target_ms": 50, "min_events": 2, "selected_ids": [3, 7], "achieved_coverage": 55}
```

When unreachable:
```json
{"start": 0, "end": 99, "target_ms": 90, "min_events": null, "selected_ids": [], "achieved_coverage": 40}
```

**Response 400:** missing/non-integer params; `start > end`; or `target_ms < 1`.

## §25 Earliest Available Slot (`GET /earliest_available`)

Find the earliest instant `T >= after` such that no stored event is active during `[T, T + duration_ms - 1]`. The answer always exists because the timeline is unbounded past the last event.

Algorithm:

1. Fetch all events with `end_ms >= after`. If none exist, return `slot_start = after`, `slot_end = after + duration_ms - 1`.
2. Clip each event's start to `max(start_ms, after)` (end_ms is unchanged). Sort by clipped start ascending.
3. Merge the clipped busy intervals (using the §11 strict-overlap rule: merge when `next.start <= prev.end`).
4. Scan the gaps: initialise `current = after`. For each merged interval `[bs, be]` in order:
   - If `bs - current >= duration_ms`, the gap `[current, bs - 1]` is wide enough. Return `slot_start = current`, `slot_end = current + duration_ms - 1`.
   - Else set `current = be + 1`.
5. After all merged intervals, return `slot_start = current`, `slot_end = current + duration_ms - 1`.

**Response 200 (JSON):**
```json
{"after": 1000, "duration_ms": 500, "slot_start": 2500, "slot_end": 2999}
```

**Response 400:** missing/non-integer params; or `duration_ms < 1`.

## §26 R-Machine Interval Partitioning (`GET /room_schedule`)

Among events **fully contained** in `[start, end]` (`start_ms >= start AND end_ms <= end`), assign as many events as possible to one of `rooms` identical, interchangeable rooms such that no two events assigned to the same room overlap (the §6 relation — touching is not allowed, matching §9). Some events may be left unscheduled. The goal is to **maximize the number of scheduled events** (not to schedule all of them).

This is strictly harder than §9 (which is the `rooms = 1` special case): with more than one room, a single earliest-finishing-time greedy is not enough — the algorithm must track the availability of every room independently.

Algorithm (deterministic greedy, optimal for the count-maximization objective):

1. Fetch the contained events sorted by `end_ms ASC`, then `id ASC`.
2. Maintain an array `room_end[0..rooms-1]`, all initially "free" (no event yet assigned).
3. For each event `e` in order:
   a. A room `r` is *available* for `e` if it is free, or `room_end[r] < e.start_ms` (strictly — touching does not free the room).
   b. If no room is available, `e` is **rejected** (left unscheduled).
   c. Otherwise, assign `e` to the available room with the **largest** `room_end[r]` (a free room counts as `-infinity`, i.e. it is only chosen when no busy-but-available room exists); ties broken by the **smallest room index**. Set `room_end[r] = e.end_ms`.
4. `max_scheduled` is the number of events assigned to a room.

This greedy is optimal because rooms are interchangeable: processing events in finishing-time order and accepting whenever any room is free never forecloses a strictly better later assignment (the same exchange argument that proves the single-machine §9 greedy optimal, applied per available room). The specific "largest `room_end[r]`" tie-break only affects *which* room number is reported, never the achieved count.

Room numbers are `0`-based. When `rooms = 1` this reduces exactly to §9 (`max_scheduled` equals `max_non_overlapping`'s count).

**Response 200 (JSON):**
```json
{"start": 1000, "end": 9000, "rooms": 2, "max_scheduled": 3, "assignments": [
  {"id": 1, "room": 0},
  {"id": 2, "room": 1},
  {"id": 3, "room": 0}
]}
```
- `assignments` — one entry per scheduled event (rejected events are omitted entirely), sorted by `id` ASC.

**Response 400:** missing/non-integer `start`, `end`, or `rooms`; `start > end`; or `rooms < 1`.

## §27 Overlap-Graph Connected Components (`GET /overlap_components`)

Build an undirected graph whose vertices are the events **intersecting** `[start, end]` (`start_ms <= end AND end_ms >= start`) and whose edges connect every pair of events `(a, b)` satisfying the §6 overlap relation (`a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms`). Report the **connected components** of this graph.

Unlike every other endpoint in this contract (all of which reduce to a sweep over `c(t)`, a single-machine or single-resource greedy, or a DP), this requires computing graph connectivity: two events can be indirectly linked through a chain of pairwise overlaps even when they do not themselves overlap (e.g. event A overlaps B, B overlaps C, but A and C do not overlap — A, B, and C are still one component).

Algorithm:

1. Fetch the events intersecting `[start, end]`.
2. Build the overlap graph described above (an edge exists between every pair with `a.start_ms <= b.end_ms AND b.start_ms <= a.end_ms`).
3. Compute connected components (e.g. via union-find or BFS/DFS over the adjacency).
4. For each component, compute `min_start_ms` = the minimum `start_ms` and `max_end_ms` = the maximum `end_ms` over the component's member events (the **raw**, unclipped event bounds — not clipped to `[start, end]`), and `event_ids` = the member IDs sorted ascending.
5. Sort the components by `min_start_ms` ASC (components partition the intersecting events, so this order is unambiguous); number them `component_id = 0, 1, 2, ...` in that order.

When no events intersect the window, `components` is `[]`.

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "components": [
  {"component_id": 0, "event_ids": [1, 2], "min_start_ms": 0, "max_end_ms": 15},
  {"component_id": 1, "event_ids": [5], "min_start_ms": 40, "max_end_ms": 50}
]}
```

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

## §28 Depth Profile (`GET /depth_profile`)

For each distinct concurrency level (depth) present in the window `[start, end]`, report the total milliseconds during which exactly that many events are simultaneously active.

**Algorithm:**

1. Build the sweep-line change-point set for `[start, end]` (same method as §23): collect `start` and `end + 1`; for every event intersecting the window add its `start_ms` if it falls in `(start, end]` and add `end_ms + 1` if it falls in `(start, end]`.
2. Sort the change points. For each consecutive pair `[cp_i, cp_{i+1})`, count the concurrency depth `c` (number of events active at `cp_i`) and add `cp_{i+1} − cp_i` to `depth_total[c]`.
3. Produce one profile entry per depth level from `0` to `max_depth` (inclusive). Depth `0` is **always** present even if its `total_ms` is zero (i.e. the window is fully covered at depth ≥ 1).
4. Sort profile by `depth` ASC.

**Conservation invariant:** `sum(p.total_ms for p in profile) == total_ms` (exactly the full window width).

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "total_ms": 100, "max_depth": 2,
 "profile": [
   {"depth": 0, "total_ms": 10},
   {"depth": 1, "total_ms": 60},
   {"depth": 2, "total_ms": 30}
 ]}
```

- `total_ms` — `end − start + 1`.
- `max_depth` — maximum concurrency in the window; `0` if no events intersect.
- `profile` — one entry per depth from `0` to `max_depth`; sorted `depth` ASC.

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.

## §29 Window Statistics (`GET /window_stats`)

Compute statistical properties of the concurrency distribution over the window `[start, end]`.

**Algorithm:**

1. Build the sweep-line RLE runs for `[start, end]` (same method as §23). Let `total_ms = end − start + 1`.
2. `covered_ms` — total milliseconds where depth ≥ 1.
3. `max_depth` — peak concurrency; equals §8's `max_concurrency`.
4. `mean_depth` — **population** weighted mean: `Σ(run.duration_ms × run.concurrency) / total_ms`. Divide by `total_ms`, **not** by the number of runs.
5. `variance_depth` — **population** variance: `Σ(run.duration_ms × (run.concurrency − mean_depth)²) / total_ms`. Divide by `total_ms`; depth-0 runs (free time) contribute to the sum.
6. `p50_depth` — the concurrency at position `floor((total_ms − 1) / 2)` (0-indexed from `start`). Walk the runs in order; the first run for which the cumulative position count exceeds `floor((total_ms − 1) / 2)` yields `p50_depth`. Free (depth-0) instants count toward the position index.

Float fields (`mean_depth`, `variance_depth`) are formatted with `%.6g` (6 significant figures).

**Response 200 (JSON):**
```json
{"start": 0, "end": 99, "total_ms": 100,
 "covered_ms": 80, "max_depth": 2,
 "mean_depth": 1.2, "variance_depth": 0.36, "p50_depth": 1}
```

**Response 400:** missing/non-integer `start` or `end`, or `start > end`.
