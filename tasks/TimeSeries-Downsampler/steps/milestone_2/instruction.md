# Milestone 2: Overlapping Sliding Windows

Your second task is to implement the sliding window logic in `src/sliding.rs`.

Unlike tumbling windows, sliding windows overlap. A single event can contribute to multiple windows simultaneously.
For example, if `window_size_ms = 300000` (5 mins) and `slide_size_ms = 60000` (1 min), an event at `300000` falls into 5 windows starting at: `60000`, `120000`, `180000`, `240000`, and `300000`.

Network streams often contain duplicate events. The Sliding Window must **aggregate duplicates** using a Bitwise XOR penalty. If the same `event_id` arrives twice or more within the same sliding window boundary, you must combine their values by taking the bitwise XOR of their IEEE-754 double precision bit representations. For example, `new_effective_value = f64::from_bits(old_value.to_bits() ^ incoming_value.to_bits())`. This combined effective value is then treated as a single data point for that `event_id` when calculating the window's final min, max, avg, count, and Exact Median.

Fix `SlidingWindowAggregator::add_event` to insert the event into all valid window starts, updating the aggregated effective value using bitwise XOR for the `event_id` if that specific window start has already seen it.
A window start `w_start` is valid for `event.timestamp_ms` if:
1. `w_start` is a multiple of `slide_size_ms`.
2. `w_start <= event.timestamp_ms`.
3. `w_start + window_size_ms > event.timestamp_ms`.

Implement `flush_window` to retrieve, compute stats (including Exact Median exactly as in M1), and clear a specific window start.
