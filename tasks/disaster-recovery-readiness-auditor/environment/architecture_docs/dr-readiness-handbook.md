# Disaster Recovery Readiness Handbook

Machine-readable canonical rows in the corpus override narrative prose when they conflict. All scan filters, manifest gates, evidence tie-breaks, blocker deduplication, scoring weights, and output schemas are defined in `/app/architecture_docs/dr-audit-policy.json`. Assessment annex rows in `/app/compliance_requirements/regional-failover-policy.md` supplement that policy; on conflict within the annex, later rows in corpus scan order win.

## Canonical record formats

RTO_TARGET `<system>` `<minutes>` `<tier>` `<source_relpath>`
RPO_TARGET `<system>` `<minutes>` `<tier>` `<source_relpath>`
AUDIT_SCOPE `<system>` `<source_relpath>`
BACKUP_RESULT `<ts_utc>` `<system>` `<region>` `<success|failure|partial>` `<recovery_minutes>` `<data_loss_minutes>` `<source_relpath>`
REPLICATION_LAG `<ts_utc>` `<system>` `<source_region>` `<target_region>` `<lag_seconds>` `<source_relpath>`
RECOVERY_TEST `<ts_utc>` `<system>` `<passed|failed>` `<actual_rto_min>` `<actual_rpo_min>` `<source_relpath>`
RESTORE_CHECKPOINT `<ts_utc>` `<system>` `<passed|failed>` `<data_loss_minutes>` `<source_relpath>`
RUNBOOK_STATUS `<system>` `<current|outdated|missing|draft|superseded>` `<last_review>` `<source_relpath>`
FAILOVER_DEP `<system>` depends_on `<dependency>` blocker_if_missing `<gate>` `<source_relpath>`
FAILOVER_STEP `<ts_utc>` `<system>` `<action>` `<source_region>` `<target_region>` `<elapsed_minutes>` `<source_relpath>`
FAILOVER_STEP `<ts_utc>` `<system>` blocked `<depends_on>` `<blocker_gate>` `<source_relpath>`
MONITORING_PROBE `<ts_utc>` `<system>` `<scenario>` `<recovery_minutes>` `<source_relpath>`
GAP_FLAG `<system>` `<gap_type>` `<detail>` `<source_relpath>`

## Normalization

Strip leading `- ` or backticks from lines before matching. Skip template lines containing `<` and `>`. Scan corpus directories in the order listed in `corpus_scan_directories` within the policy file, each in sorted path order.

## Scoped systems

Assess only systems that pass every gate in `manifest_gates` and have a matching `AUDIT_SCOPE` row in the corpus scan. Ignore all metrics, runbooks, and blockers for systems that fail any gate.

## Assessment summary

For each scoped system, observed RTO and RPO minutes are the maximum across all qualifying peer evidence sources defined in the compliance annex and policy — not a fallback chain. `meets_rto` applies `critical_rto_grace_minutes` for critical-tier systems; `rto_exceeded` gaps and readiness RTO penalties use the unadjusted target. Gap `evidence_source` values follow `evidence_priority` tie rules from the policy. `failover_blockers` deduplicate by `(system, depends_on, blocker_gate)` using `blocker_source_priority` from the policy. `failover_timeline.md` includes only scoped systems when `scoped_systems_only` is true in the policy.
