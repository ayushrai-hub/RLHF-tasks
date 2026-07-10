# Priority Scoring Specification

## Weighted Violation Score (§9.1)

The weighted violation score combines severity weights with delivery priority levels. Per the Incident Response Framework §9.1:
- critical severity = 5.0
- error severity = 3.0  
- warning severity = 1.0

The raw score sums `severity_weight * delivery_priority` for each violation.

## Normalization (§9.1.2)

Per §9.1.2: the raw weighted sum is normalized by dividing by the NUMBER OF VIOLATIONS (not total deliveries). This produces a per-violation severity index independent of log volume, representing the average impact per incident.

This normalization was chosen because large delivery logs would otherwise dilute the severity signal. A system with 3 critical violations on 1000 messages should score the same per-incident severity as 3 critical violations on 100 messages.

## High Priority Violations

Violations on deliveries with priority >= 3 are flagged as high-priority violations. This threshold is fixed regardless of the deadletter_config.priority_threshold.
