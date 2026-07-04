# Storage and workload budget

Each artifact_id may appear at most min(redundancy, max_parallel_migrations) times across round 1 migration_pairs (primary or replica).
within_storage_budget is false when any artifact exceeds that cap or when migration byte total exceeds collection storage_byte_budget.
