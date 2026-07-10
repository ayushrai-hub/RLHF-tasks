Output schema for results.json:

summary: total_deliveries, unsub_violations, duplicate_violations, ordering_violations, dead_lettered, num_violations, num_topics, all_valid

violations (sorted by type then delivery_id): type, delivery_id, client_id, topic, details, severity

topic_stats (sorted by topic): topic, deliveries, unique_clients, violations

metrics: unsub_rate, duplicate_rate, ordering_rate, violation_rate, avg_mean_interval, avg_fanout, ack_rate, dead_letter_rate, avg_backpressure, weighted_violation_score

latency (sorted by topic): topic, mean_interval, max_gap

fanout (sorted by topic): topic, unique_messages, total_deliveries, fanout_ratio

ack_stats: total_acked, total_unacked, ack_rate

dead_letter: total_dead_lettered, by_retry_exhaustion, by_ttl_expiry, dead_letter_rate

priority: weighted_violation_score, priority_distribution, avg_priority, high_priority_violations

backpressure (sorted by topic): topic, burst_windows, max_burst_size, backpressure_index

throttle (sorted by topic): topic, delivery_rate, throttle_events, peak_rate

retention: total_expired, expiry_rate, max_age (over expired-only subset where age > TTL), avg_age (over expired-only subset where age > TTL)
