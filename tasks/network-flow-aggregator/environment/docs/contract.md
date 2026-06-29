# Network Flow Aggregator Contract

## Pipeline Stages

1. **Parse**: CSV → FlowRecord
2. **Aggregate**: FlowRecord → FlowAggregate (grouped by protocol)
3. **Classify**: FlowAggregate → FlowClassification (risk scoring)
4. **Emit**: JSON report with aggregates + classifications

## Data Types

- FlowRecord: src_ip, dst_ip, src_port, dst_port, protocol, bytes, packets, timestamp
- FlowAggregate: protocol, total_bytes, total_packets, flow_count, unique_pairs
- FlowClassification: category, risk_score (0-100), details

## Expected Behavior

- Parse all 30 trace records without loss
- Aggregate accurately by protocol (TCP, UDP)
- Classify with correct risk scores
- Emit complete JSON report
