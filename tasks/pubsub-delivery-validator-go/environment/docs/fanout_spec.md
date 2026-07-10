# Fan-out Specification

## Fan-out Ratio Computation (§5.2)

Per the Pub/Sub QoS Specification §5.2, fan-out ratio measures how many times each unique message is delivered across all subscribers. The ratio is computed as `total_deliveries / unique_messages` per topic using floating-point division. This captures the replication factor achieved by the broker's fan-out mechanism.

## Average Fan-out

The `avg_fanout` metric averages all per-topic fan-out ratios to 4 decimal places. High fan-out (> 2.0) indicates efficient topic-level multicast. Low fan-out (≈ 1.0) suggests point-to-point delivery patterns.

## Interaction with Duplicate Detection

Fan-out and duplicate detection are orthogonal: fan-out measures legitimate multi-subscriber delivery (same msg_id to DIFFERENT clients), while duplicates flag redelivery to the SAME client. A message delivered to 3 clients produces fanout_ratio contribution but zero duplicate violations.

## Interaction with Dead Letter Queue

Dead-lettered messages still contribute to fan-out ratio computation. The fan-out captures broker dispatch behavior regardless of downstream processing outcomes.
