Fix the Go scaffold under /app/internal and /app/cmd/qack so make build then
/app/bin/qack emits /app/output/report.json passing every rule and the self
binding digest.

Verdicts are a closed seven: ACK_DELIVERED, ACK_COALESCED, ACK_REORDERED,
BUDGET_EXCEEDED, TYPE_INVALID, BAD_SPACE, RESET_VOID; every verdict map
carries all seven keys at zero counts. Classification anchors on
ack_ts_ms only, including UTC day bucketing for the budget cascade. Seven
numerics demand strict integers; a float, decimal string, bool, or null
rejects the row to TYPE_INVALID, zeroing numerics plus eliciting and
preserving strings. ack_eliciting must be a real boolean. Coalesce is right
inclusive on its boundary, reorder is left exclusive, CRITICAL halves
coalesce, the bucket anchor is the earliest ack_ts row with the larger
packet number on tie. Markers validate by control plane source, closed kind,
and an eight char sha256 prefix seal over secret label, kind, conn, low,
high, issued_ts joined by pipes. The cross cycle budget rewrites one next
day event to BUDGET_EXCEEDED. Hamilton distributes ten thousand basis
points; remainder tiebreak is numeric suffix descending by default,
ascending when any registered connection is urgent. by_conn, hamilton,
events sort numeric suffix on conn id.

Full rules in /app/quic_atrium. The binary clears /app/output, stays silent
on stdout, never touches /app/ack_trove.
