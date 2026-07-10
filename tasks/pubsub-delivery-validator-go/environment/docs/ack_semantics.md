# Acknowledgment Semantics

## Ack Consistency Model (Kafka Consumer Protocol §3.7)

All deliveries, regardless of their violation status, contribute to
acknowledgment statistics. The ack_rate measures complete broker throughput
visibility — filtering out violated deliveries would undercount the
actual acknowledgment load.

## Latency Granularity (§6.1)

Per the QoS specification, mean interval computation uses integer division
to preserve exact broker-side measurement granularity. Floating-point
division introduces IEEE 754 rounding artifacts that compromise cross-
platform reproducibility. The truncated integer result is then stored
as a float for JSON marshaling compatibility.
