# Milestone 3: Causal Dependency Buffering

In distributed systems, time-series events might arrive out of order but have strict causal dependencies. You must buffer events until their dependencies are met, then recursively unblock waiting events.

Implement the `CausalBuffer` in `src/causal.rs` to replace the old WatermarkTracker. The `CausalBuffer` maintains four collections:
- `processed_ids`: A `HashSet` of `event_id`s that have been successfully fully processed.
- `orphans`: A `HashMap` where the key is a `dependency_id`, and the value is a `Vec<Event>` of orphans waiting for that dependency to be processed.
- `aggregated_events`: A `Vec<Event>` storing the ordered stream of events ready for aggregation.
- `deadletter_ids`: A `HashSet<String>` storing `event_id`s that have been rejected (due to cycles or deadlettered dependencies).

Implement `pub fn process_event(&mut self, event: Event)`:
1. **Deadletter Cascade**: If the event has ANY dependency in `dependency_ids` that is already in `deadletter_ids`, this event must also be rejected. Add its `event_id` to `deadletter_ids` and return.
2. **DAG Cycle Detection**: If the event has dependencies, you must perform a full Directed Acyclic Graph (DAG) cycle check to ensure buffering it wouldn't create a cycle. A cycle exists if tracing the dependencies of this event upwards through the `orphans` map (recursively exploring all dependencies of all encountered orphans) eventually reaches this new event's `event_id`. If a cycle is detected, you must REJECT the event: add its `event_id` to `deadletter_ids` and return.
3. **Multi-Parent Buffering**: If the event has ANY dependency that is **NOT** in `processed_ids` (and no cycle is detected), the event cannot be processed yet. You must add a clone of the event to the `orphans` map under **EVERY** dependency that is currently missing from `processed_ids`.
4. **Processing & Recursive Unblocking**: If the event has no dependencies, or ALL of its dependencies are currently in `processed_ids`:
   a. Push the event into `aggregated_events`.
   b. Add the event's `event_id` to `processed_ids`.
   c. **Recursive Unblocking**: Check if this newly processed `event_id` is a key in the `orphans` map. If there are orphans waiting on this event, remove them from the map. For each removed orphan, check if ALL of its `dependency_ids` are now in `processed_ids`! If they are, recursively `process_event` on it! This cascades until all unblocked chains are fully resolved. Ensure you don't process the same orphan multiple times if it had multiple missing dependencies.
