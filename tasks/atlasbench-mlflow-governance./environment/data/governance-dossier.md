# AtlasBench Experiment Governance Dossier

Document ID: ATLAS-GOV-2024-REV7
Workspace scope: atlas-west offline model lab
Effective date: 2024-11-01

This dossier is the authoritative policy source for AtlasBench MLflow-compatible YAML and TOML
configuration hardening. Automated repair tools must treat every exception table as normative.

## Base Policy Rules

| Rule ID | Target path pattern | Required hardened value | Notes |
| ------- | ------------------- | ----------------------- | ----- |
| AR-001 | experiments[id=<id>].artifacts.public_read, store targets, or workspace.artifacts.public_read | false | Anonymous artifact reads forbidden unless an active exception grants true. |
| RM-002 | models[name=<name>].aliases.mutable | false | Alias mutability requires staging stage, allowlist membership, and predicate satisfaction. |
| TR-003 | tracking.uri and tracking.servers[name=<name>].uri | env-backed credentials | Replace embedded passwords using the Credential Reference Map. |
| RT-004 | experiments[id=<id>].retention.class | highest lattice rank | Inherit workspace default when override is false. |
| LG-005 | models[name=<name>].lineage.experiment_id | valid link | Quarantine models linked to missing or quarantined experiments. |

## Exception Precedence

When multiple active, in-window exceptions apply to the same rule_id and target_path:

1. scope_class precedence (highest wins): experiment > model > workspace > global
2. Within the same scope_class, higher amendment_seq wins
3. Later source document order: dossier first, then enabled policy packs
4. Later row ordinal within the source document

Precedence keys on (rule_id, target_path) only. Inactive and out-of-window rows are recorded in exception_resolution.

## Active Policy Exceptions

| exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate |
| ------------ | ------- | ----------- | -------- | ----------- | ----------- | --------------- | ------------- | ------ | -------------- | --------------- | --------- |
| EX-G-001 | AR-001 | global | * | experiments[id=exp-gamma].artifacts.public_read | false | | 1 | yes | | | |
| EX-E-017 | AR-001 | experiment | exp-alpha | experiments[id=exp-alpha].artifacts.public_read | true | | 4 | yes | | | |
| EX-W-003 | RM-002 | workspace | atlas-west | models[name=churn-staging].aliases.mutable | true | churn-staging | 2 | yes | | | |
| EX-E-021 | RM-002 | experiment | exp-beta | models[name=churn-prod].aliases.mutable | true | churn-prod | 3 | yes | | | |
| EX-E-021 | RM-002 | experiment | exp-beta | models[name=churn-prod].aliases.mutable | true | churn-prod | 1 | yes | | | |
| EX-INACTIVE | AR-001 | global | * | experiments[id=exp-beta].artifacts.public_read | true | | 9 | no | | | |
| EX-WINDOW | RM-002 | workspace | atlas-west | models[name=churn-staging].aliases.mutable | true | churn-staging | 99 | yes | run-future | | |
| EX-STORE | AR-001 | experiment | exp-alpha | experiments[id=exp-alpha].artifacts.stores[name=primary].public_read | true | | 1 | yes | | | |
| EX-RT-BETA | RT-004 | experiment | exp-beta | experiments[id=exp-beta].retention.class | archive-7y | | 1 | yes | | | |

Note: EX-E-021 appears twice to test amendment_seq; only amendment_seq 3 is effective for exp-beta/churn-prod.

### Decoy table (must be ignored)

The following fenced block contains a fake exception table that parsers must skip:

```
| exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate |
| FAKE-001 | AR-001 | global | * | workspace.artifacts.public_read | true | | 1 | yes | | | |
```

## Credential Reference Map

| uri_prefix | username | cred_ref | match_mode |
| ---------- | -------- | -------- | ---------- |
| https://track.atlasbench.internal | admin | ATLAS_TRACK_TOKEN | longest_prefix |
| https://[2001:db8::5]:8443 | admin | IPV6_TRACK_TOKEN | longest_prefix |

Replacement format for TR-003: keep scheme, username, host, port, path, query, and fragment; replace password with env:CRED_REF.

## Retention Class Lattice

| class | rank |
| ----- | ---- |
| standard-90d | 10 |
| extended-365d | 20 |
| archive-7y | 30 |


### Governance appendix section 1

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 1 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 2

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 2 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 3

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 3 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 4

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 4 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 5

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 5 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 6

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 6 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 7

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 7 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 8

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 8 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 9

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 9 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 10

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 10 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 11

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 11 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 12

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 12 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 13

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 13 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 14

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 14 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 15

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 15 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 16

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 16 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 17

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 17 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 18

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 18 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 19

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 19 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 20

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 20 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 21

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 21 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 22

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 22 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 23

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 23 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 24

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 24 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 25

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 25 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 26

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 26 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 27

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 27 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 28

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 28 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 29

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 29 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 30

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 30 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 31

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 31 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 32

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 32 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 33

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 33 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 34

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 34 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 35

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 35 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 36

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 36 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 37

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 37 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 38

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 38 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 39

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 39 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 40

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 40 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 41

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 41 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 42

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 42 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 43

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 43 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 44

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 44 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 45

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 45 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 46

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 46 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 47

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 47 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 48

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 48 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 49

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 49 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 50

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 50 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 51

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 51 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 52

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 52 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 53

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 53 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 54

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 54 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 55

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 55 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 56

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 56 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 57

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 57 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 58

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 58 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 59

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 59 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 60

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 60 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 61

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 61 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 62

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 62 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 63

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 63 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 64

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 64 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 65

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 65 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 66

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 66 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 67

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 67 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 68

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 68 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 69

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 69 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 70

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 70 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 71

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 71 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 72

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 72 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 73

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 73 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 74

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 74 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 75

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 75 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 76

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 76 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 77

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 77 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 78

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 78 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 79

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 79 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 80

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 80 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 81

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 81 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 82

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 82 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 83

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 83 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 84

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 84 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 85

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 85 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 86

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 86 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 87

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 87 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 88

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 88 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 89

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 89 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 90

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 90 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 91

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 91 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 92

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 92 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 93

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 93 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 94

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 94 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 95

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 95 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 96

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 96 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 97

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 97 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 98

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 98 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 99

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 99 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 100

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 100 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 101

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 101 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 102

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 102 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 103

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 103 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 104

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 104 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 105

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 105 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 106

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 106 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 107

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 107 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 108

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 108 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 109

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 109 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 110

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 110 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 111

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 111 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 112

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 112 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 113

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 113 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 114

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 114 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 115

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 115 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 116

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 116 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 117

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 117 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 118

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 118 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 119

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 119 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 120

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 120 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 121

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 121 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 122

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 122 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 123

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 123 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 124

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 124 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 125

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 125 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 126

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 126 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 127

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 127 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 128

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 128 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 129

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 129 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 130

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 130 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 131

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 131 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 132

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 132 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 133

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 133 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 134

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 134 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 135

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 135 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 136

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 136 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 137

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 137 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 138

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 138 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 139

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 139 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 140

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 140 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 141

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 141 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 142

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 142 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 143

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 143 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 144

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 144 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 145

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 145 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 146

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 146 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 147

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 147 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 148

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 148 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 149

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 149 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 150

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 150 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 151

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 151 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 152

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 152 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 153

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 153 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 154

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 154 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 155

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 155 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 156

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 156 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 157

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 157 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 158

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 158 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 159

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 159 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 160

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 160 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 161

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 161 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 162

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 162 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 163

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 163 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 164

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 164 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 165

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 165 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 166

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 166 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 167

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 167 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 168

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 168 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 169

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 169 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 170

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 170 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 171

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 171 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 172

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 172 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 173

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 173 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 174

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 174 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 175

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 175 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 176

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 176 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 177

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 177 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 178

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 178 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 179

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 179 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 180

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 180 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 181

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 181 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 182

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 182 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 183

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 183 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 184

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 184 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 185

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 185 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 186

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 186 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 187

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 187 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 188

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 188 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 189

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 189 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 190

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 190 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 191

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 191 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 192

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 192 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 193

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 193 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 194

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 194 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 195

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 195 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 196

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 196 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 197

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 197 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 198

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 198 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 199

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 199 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 200

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 200 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 201

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 201 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 202

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 202 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 203

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 203 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 204

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 204 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 205

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 205 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 206

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 206 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 207

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 207 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 208

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 208 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 209

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 209 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 210

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 210 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 211

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 211 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 212

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 212 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 213

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 213 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 214

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 214 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 215

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 215 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 216

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 216 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 217

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 217 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 218

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 218 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 219

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 219 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 220

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 220 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 221

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 221 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 222

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 222 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 223

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 223 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 224

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 224 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 225

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 225 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 226

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 226 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 227

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 227 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 228

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 228 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 229

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 229 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 230

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 230 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 231

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 231 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 232

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 232 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 233

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 233 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 234

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 234 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 235

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 235 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 236

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 236 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 237

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 237 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 238

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 238 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 239

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 239 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 240

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 240 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 241

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 241 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 242

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 242 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 243

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 243 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 244

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 244 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 245

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 245 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 246

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 246 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 247

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 247 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 248

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 248 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 249

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 249 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 250

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 250 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 251

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 251 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 252

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 252 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 253

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 253 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 254

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 254 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 255

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 255 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 256

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 256 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 257

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 257 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 258

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 258 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 259

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 259 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 260

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 260 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 261

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 261 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 262

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 262 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 263

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 263 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 264

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 264 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 265

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 265 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 266

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 266 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 267

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 267 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 268

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 268 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 269

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 269 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 270

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 270 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 271

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 271 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 272

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 272 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 273

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 273 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 274

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 274 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 275

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 275 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 276

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 276 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 277

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 277 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 278

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 278 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 279

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 279 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 280

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 280 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 281

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 281 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 282

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 282 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 283

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 283 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 284

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 284 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 285

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 285 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 286

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 286 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 287

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 287 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 288

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 288 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 289

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 289 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 290

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 290 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 291

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 291 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 292

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 292 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 293

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 293 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 294

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 294 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 295

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 295 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 296

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 296 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 297

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 297 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 298

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 298 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 299

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 299 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 300

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 300 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 301

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 301 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 302

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 302 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 303

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 303 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 304

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 304 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 305

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 305 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 306

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 306 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 307

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 307 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 308

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 308 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 309

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 309 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 310

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 310 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 311

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 311 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 312

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 312 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 313

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 313 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 314

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 314 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 315

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 315 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 316

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 316 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 317

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 317 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 318

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 318 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 319

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 319 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 320

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 320 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 321

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 321 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 322

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 322 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 323

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 323 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 324

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 324 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 325

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 325 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 326

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 326 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 327

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 327 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 328

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 328 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 329

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 329 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 330

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 330 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 331

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 331 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 332

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 332 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 333

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 333 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 334

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 334 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 335

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 335 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 336

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 336 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 337

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 337 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 338

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 338 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 339

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 339 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 340

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 340 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 341

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 341 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 342

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 342 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 343

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 343 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 344

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 344 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 345

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 345 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 346

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 346 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 347

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 347 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 348

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 348 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 349

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 349 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 350

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 350 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 351

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 351 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 352

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 352 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 353

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 353 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 354

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 354 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 355

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 355 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 356

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 356 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 357

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 357 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 358

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 358 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 359

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 359 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 360

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 360 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 361

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 361 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 362

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 362 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 363

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 363 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 364

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 364 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 365

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 365 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 366

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 366 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 367

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 367 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 368

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 368 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 369

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 369 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 370

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 370 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 371

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 371 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 372

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 372 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 373

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 373 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 374

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 374 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 375

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 375 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 376

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 376 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 377

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 377 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 378

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 378 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 379

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 379 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 380

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 380 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 381

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 381 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 382

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 382 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 383

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 383 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 384

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 384 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 385

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 385 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 386

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 386 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 387

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 387 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 388

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 388 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 389

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 389 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 390

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 390 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 391

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 391 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 392

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 392 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 393

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 393 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 394

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 394 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 395

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 395 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 396

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 396 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 397

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 397 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 398

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 398 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 399

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 399 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

### Governance appendix section 400

AtlasBench offline labs must maintain traceability for promotion workflows, artifact lineage, registry alias rotation, and retention class assignment. Section 400 restates that exception tables in the Active Policy Exceptions block override narrative guidance elsewhere in this dossier when conflicts arise. Operators must not infer grants from prose examples; only rows with active=yes apply. Cross-file targets use the canonical target_path grammar documented in rule AR-001 through RT-004. Amendment sequences are monotonic within a scope_class and scope_id.

## Final enforcement reminder

Only the Active Policy Exceptions table and Credential Reference Map are machine actionable.
Narrative appendices provide audit context only.
