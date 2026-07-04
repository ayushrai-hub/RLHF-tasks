# Regional Failover Compliance Requirements

Authoritative recovery objectives for production systems.

RTO_TARGET analytics-pipeline 240 standard compliance_requirements/regional-failover-policy.md
RPO_TARGET analytics-pipeline 360 standard compliance_requirements/regional-failover-policy.md
RTO_TARGET cache-cluster 10 critical compliance_requirements/regional-failover-policy.md
RPO_TARGET cache-cluster 0 critical compliance_requirements/regional-failover-policy.md
RTO_TARGET identity-core 30 critical compliance_requirements/regional-failover-policy.md
RPO_TARGET identity-core 15 critical compliance_requirements/regional-failover-policy.md
RTO_TARGET notification-hub 45 standard compliance_requirements/regional-failover-policy.md
RPO_TARGET notification-hub 60 standard compliance_requirements/regional-failover-policy.md
RTO_TARGET order-api 60 standard compliance_requirements/regional-failover-policy.md
RPO_TARGET order-api 30 standard compliance_requirements/regional-failover-policy.md
RTO_TARGET payments-ledger 15 critical compliance_requirements/regional-failover-policy.md
RPO_TARGET payments-ledger 5 critical compliance_requirements/regional-failover-policy.md
RTO_TARGET search-index 120 standard compliance_requirements/regional-failover-policy.md
RPO_TARGET search-index 120 standard compliance_requirements/regional-failover-policy.md

AUDIT_SCOPE analytics-pipeline compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE cache-cluster compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE identity-core compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE notification-hub compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE order-api compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE payments-ledger compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE search-index compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE settlement-router compliance_requirements/regional-failover-policy.md
AUDIT_SCOPE archival-warehouse compliance_requirements/regional-failover-policy.md
RTO_TARGET archival-warehouse 60 standard compliance_requirements/regional-failover-policy.md
RTO_TARGET settlement-router 20 critical compliance_requirements/regional-failover-policy.md
RPO_TARGET settlement-router 10 critical compliance_requirements/regional-failover-policy.md

## Assessment annex

Machine-readable lines here supplement `/app/architecture_docs/dr-readiness-handbook.md`. On conflict within this annex, later rows in corpus scan order win.

RUNBOOK_STATUS resolution: the last `RUNBOOK_STATUS` row per system in corpus scan order is authoritative. A terminal `current` row clears any earlier `outdated` or `missing` issue for that system.

BACKUP_RESULT resolution: qualifying rows require `ts_utc` on or before `assessment_date_utc` and primary region per the handbook. Treat `partial` backup rows like `failure` rows when deciding whether failure-only resolution applies and when selecting backup-derived metrics. When a system has at least one qualifying `failure` or `partial` row, ignore all `success` rows for that system's backup-derived RTO and RPO contributions; when no qualifying `failure` or `partial` row exists, use `success` rows.

Recovery drill rows: only rows with status `failed` contribute to observed RTO or RPO. Failed drill metrics participate in the same peer maximum as backup, failover-step, and monitoring evidence — they do not override lower backup values, but any higher drill value becomes the observed maximum.

FAILOVER_STEP scope: only rows whose source_relpath is `incident_postmortems/regional-outage-2026-03.md` contribute to observed RTO, failover_timeline.md, or blocked failover_blockers entries. Ignore other `FAILOVER_STEP` rows. Blocked postmortem steps use the blocked canonical format (`FAILOVER_STEP ... blocked <depends_on> <blocker_gate> ...`); emit them in failover_timeline.md with `action` set to `blocked`, map dependency and gate into source_region and target_region, and set elapsed_minutes to 0.

FAILOVER_BLOCKER deduplication: when building failover_blockers, scan FAILOVER_DEP rows and scoped blocked FAILOVER_STEP rows in corpus order. Deduplicate by (system, depends_on, blocker_gate). When the same tuple appears more than once, keep the row whose source class has the higher rank in `blocker_source_priority` within `/app/architecture_docs/dr-audit-policy.json`; when ranks tie, keep the earliest matching row in corpus scan order.

REPLICATION_LAG resolution: qualifying rows follow the policy replication filters. A system's replication-derived RPO contribution is ignored unless its infrastructure manifest sets `replication_audited` to true.

Gap evidence_source: derive while walking the corpus scan that computes observed maxima. When multiple qualifying records tie on the maximum minute value, keep the source from the record with the higher `evidence_priority` class in the policy file; when priority is also tied, keep the earliest matching row in that scan.

Timeline blocked steps: elapsed_minutes is 0 in the markdown table (never blank).

Assessment window, primary-region filters, target last-wins, evidence tie-breaking, scoring weights, and output schemas remain in the handbook.

RUNBOOK_STATUS identity-core current 2026-05-20 compliance_requirements/regional-failover-policy.md

MONITORING_PROBE resolution: only rows with scenario `regional_failover` on or before the assessment window contribute to observed RTO; ignore `synthetic_drill` and all other scenario values.

Primary backup region: treat `us-east-1-primary` as equivalent to `us-east-1` for qualifying BACKUP_RESULT rows.

RPO_TARGET cache-cluster 1 critical compliance_requirements/regional-failover-policy.md

RUNBOOK_STATUS notification-hub superseded 2026-04-15 compliance_requirements/regional-failover-policy.md
