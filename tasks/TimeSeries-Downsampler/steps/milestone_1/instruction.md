# Milestone 1: Custom Parsing & Tumbling Windows

You must process a continuous stream of events. First, fix the event parser. You will need to edit `src/parser.rs` and `src/tumbling.rs`.
Events arrive as pipe-delimited strings with an optional 5th column: `TimestampMs|EventID|MetricName|Value|DependencyIDs`.
For example: `1700000000000|evt1|cpu|45.5|parent_evt1,parent_evt2` or `1700000000000|evt2|cpu|45.5|`.

**Parsing Rules:**
- Valid lines must have either 4 or 5 columns. Blank lines or lines with other field counts should be ignored (return `None` from `parse_event`).
- The `name` field may be optionally enclosed in double quotes (e.g. `100|e1|"cpu|usage"|45.0|`). If it is, any `|` characters inside the quotes are NOT delimiters, and the quotes must be stripped in the final `name` string (resulting in `cpu|usage`).
- **Base64 Values:** The 4th column (Value) may either be a standard float (e.g. `45.5`) or a base64 encoded string representing an IEEE 754 double-precision float (little-endian). If the string starts with `b64:`, you must base64-decode the remainder into an 8-byte array and read it as an `f64`.
- The fifth column is an optional comma-separated list of `dependency_ids` (Strings). If present and non-empty, map it to a `Vec<String>`. If missing or completely empty, map it to an empty `Vec<String>`.

Once parsing is done, implement the `TumblingWindowAggregator`.
The tumbling window aggregates min, max, average, count, and the **Exact Median** for a specific metric name over a fixed `window_size_ms`. A window's start time is calculated as `(timestamp_ms / window_size_ms) * window_size_ms`. The end time is `start time + window_size_ms`. 

To compute the Exact Median:
- Sort the values for the window in ascending order.
- If the number of elements $N$ is odd, the median is the middle element.
- If $N$ is even, the median is the arithmetic mean of the two middle elements.

Implement `TumblingWindowAggregator::add_event` to correctly bin incoming events, and `flush_window(window_start)` to compute the final `WindowResult`s for that timestamp and remove them from memory.
