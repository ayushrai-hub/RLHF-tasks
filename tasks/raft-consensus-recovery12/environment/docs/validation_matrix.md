# Validation Matrix (internal)

Cross-check WAL index monotonicity, RPC term correlation, and partition majority sizes before simulation. Property tests expect `linearizability_digest` stability under command reorder when ticks tie-break lexically by `node_id`.
