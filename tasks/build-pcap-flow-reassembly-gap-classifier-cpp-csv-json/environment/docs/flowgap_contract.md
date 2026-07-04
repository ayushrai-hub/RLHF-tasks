The analyzer reads a comma-separated metadata file using normal quoted-field CSV rules, including doubled quotes inside quoted fields. The first non-empty line must be the exact header:

`stream_id,packet_no,ts,src,dst,seq,ack,payload_len,flags`

Fields:

- `stream_id`, `ts`, `src`, `dst`, and `flags` are strings.
- `packet_no`, `seq`, `ack`, and `payload_len` are non-negative integers.
- `flags` is a TCP flag string using only the letters `A`, `F`, `P`, `R`, and `S`, with no repeated letters.
- Reset rows are valid only when `flags` is `R` or `AR` and `payload_len` is `0`.
- The letters `S` and `F` each consume one sequence number. A non-reset row consumes `payload_len + syn_flag + fin_flag` sequence numbers. Rows that consume zero sequence numbers are `zero_length`.
- A valid reset row consumes zero sequence numbers, is classified as `reset`, abandons open gaps for its direction, and clears sequence state for later packets in that direction.
- Blank lines before or after the header are ignored and do not count as data rows, but they still occupy CSV file line numbers.
- If the first non-empty line is not the exact header above, the CLI must exit non-zero and print `invalid csv header` on stderr.
- Non-header rows with the wrong number of fields, blank `stream_id`, invalid integers, negative values, invalid flags, duplicate packet numbers in one stream direction, or timestamp regressions in one stream direction are skipped and reported in `diagnostics`.

Output JSON must be compact, with no spaces after separators, and must end with exactly one newline. Top-level keys are `input`, `streams`, `totals`, `diagnostics`.

`input` keys are `csv`, `stream_filter`, `rows_read`, `rows_skipped`. `stream_filter` is the selected stream string or `null`.

`rows_read` counts every non-blank, non-header data row encountered, including rows that are later skipped for malformed fields and rows that do not match `--stream`. `rows_skipped` counts the malformed subset of `rows_read`.

Streams are sorted by `stream_id` ascending after any stream filter. Within each stream, sequence state is tracked independently for each direction, where direction is the exact string `<src> -> <dst>`. Duplicate packet checks and timestamp regression checks are scoped to the same `(stream_id, src, dst)` direction. Timestamp order is a simple lexicographic comparison against the last accepted row in that direction.

Each stream object uses keys `stream_id`, `segments`, `gaps`, `summary`.

Rows within each stream are processed by CSV appearance order, not by sequence number. Segment rows are emitted in that same order and use keys `packet_no`, `direction`, `seq`, `end_seq`, `payload_len`, `flags`, `status`, `expected_before`, `gap_before`, `fills_gap`.

Classification:

- For the first consuming segment in a direction, initialize `expected_before` to its `seq`.
- `zero_length`: consumed length is zero. It does not create or fill gaps.
- `reset`: flags contain `R`. It does not create or fill gaps, abandons every currently open gap in the same direction, clears that direction's sequence state, and leaves other directions untouched.
- `retransmit`: the entire interval is below or equal to `expected_before`.
- `overlap`: the segment starts before `expected_before` and extends beyond it. Only the new suffix advances the stream.
- `in_order`: the segment starts exactly at `expected_before`.
- `out_of_order`: the segment starts beyond `expected_before`; this observes a gap from `expected_before` to `seq`, but does not advance `expected_before` until the missing bytes arrive.

`gap_before` is `null` unless the segment is `out_of_order`; otherwise it is an object with keys `start`, `end`, `length` and covers `{expected_before, current_seq}` exactly. Repeated segments beyond the same missing range must not create duplicate gap objects, but each repeated segment still keeps its own `gap_before` object.

Each direction tracks every consumed interval. After an `in_order` or `overlap` segment advances `expected_before`, any already-observed higher interval in the same direction that now touches the frontier also advances it. A gap becomes `filled` when this advancement reaches its end; its `filled_by` is the packet number of the segment that caused the gap to become filled. Otherwise the gap remains `open` with `filled_by` set to `null`. A later reset in the same direction changes open gaps to `abandoned` and leaves `filled_by` as `null`.

Gap objects are emitted by first observation order with keys `direction`, `start`, `end`, `length`, `introduced_by`, `status`, `filled_by`.

Stream `summary` keys are `segments`, `directions`, `bytes_observed`, `in_order`, `out_of_order`, `retransmit`, `overlap`, `zero_length`, `reset`, `gaps`, `open_gaps`, `abandoned_gaps`. `segments` counts emitted segment rows after filtering. `directions` counts unique `src -> dst` directions with emitted rows. `bytes_observed` sums only payload bytes from emitted segment rows; SYN/FIN sequence consumption is not included in this byte total.

Top-level `totals` uses the same summary keys plus `streams`. When `--stream` names a stream that has no valid rows, `streams` is empty and every total is zero, while diagnostics from the whole CSV are still emitted. `diagnostics` is sorted by source row number ascending; `row` is the CSV file line number with the header as line 1 when there are no leading blanks, so the first data row is normally line 2. Blank physical lines still count for later diagnostic row numbers. Each diagnostic object uses keys `row`, `error`. Error text must be one of `wrong column count`, `blank stream_id`, `invalid integer`, `invalid flags`, `duplicate packet_no`, or `timestamp regression`.
