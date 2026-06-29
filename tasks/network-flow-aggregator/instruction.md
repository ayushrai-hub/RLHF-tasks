Build a network flow aggregation pipeline in Rust that parses CSV trace files, aggregates flows by protocol, classifies traffic patterns, and emits structured JSON reports.

Your pipeline must process the trace file at /app/environment/traces/sample_trace.csv through four stages: parsing, aggregation, classification, and emission. Each stage must maintain data integrity without corruption, duplication, or loss.

The workspace contains four library crates under the following directories:
- parse/ (crate name: nfa_parse) - converts CSV lines into FlowRecord structs
- aggregate/ (crate name: nfa_aggregate) - groups records by protocol and computes totals
- classify/ (crate name: nfa_classify) - assigns risk scores and categories based on volume thresholds
- emit/ (crate name: nfa_emit) - writes a JSON report with aggregates, classifications, and metadata

Requirements:
- Fix all bugs in the Rust workspace crates
- Rebuild with cargo build --workspace --release
- Run the corrected nfa_verify binary to produce output at /tmp/test_report.json
- The report must satisfy:
  - Parse all trace records without loss
  - Aggregate bytes and packets accurately per protocol
  - Count flows per protocol correctly
  - Classify flows with risk scores between 0-100
  - Emit valid JSON with keys: aggregates, classifications, total_flows, emission_hash
  - Each aggregate must have: protocol, total_bytes, total_packets, flow_count, unique_pairs
  - Each classification must have: category, risk_score, details (protocol name embedded in details string)
  - All values must match the trace data accurately
- Do not modify test files or trace data

Build with cargo build --release and run the verifier binary to process traces. Your fixed code must produce accurate aggregation results matching the trace data, maintain data integrity across all pipeline stages, and emit reports that pass all verifier tests.
