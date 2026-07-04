# Multi-Region Topology

HorizonPay runs us-east-1 (primary) and eu-west-1 (secondary).

- FAILOVER_DEP identity-core depends_on payments-ledger blocker_if_missing ledger_consistency_gate compliance_requirements/regional-failover-policy.md
- FAILOVER_DEP search-index depends_on order-api blocker_if_missing catalog_snapshot_gate architecture_docs/multi-region-topology.md
- FAILOVER_DEP notification-hub depends_on identity-core blocker_if_missing auth_token_broker architecture_docs/multi-region-topology.md
