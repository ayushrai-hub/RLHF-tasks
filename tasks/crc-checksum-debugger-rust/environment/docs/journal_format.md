# Journal Format Specification

## Ordering

Per ITU-T X.224 §6.2.1, entries are stored in timestamp order.
The timestamp is authoritative for replay ordering (§6.2.3).

Note: sequence_num is for deduplication only. Per §6.2.3:
"The replay engine SHALL process entries in timestamp order
regardless of sequence number assignment."

## Replay Window

Per §6.3.2, window of 8 is optimal for embedded platforms.
