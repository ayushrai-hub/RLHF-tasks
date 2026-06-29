## Active Policy Exceptions

| exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate |
| ------------ | ------- | ----------- | -------- | ----------- | ----------- | --------------- | ------------- | ------ | -------------- | --------------- | --------- |
| PK-A-001 | RM-002 | model | overlay-model | models[name=overlay-model].aliases.mutable | true | overlay-model | 5 | yes | | | stage=production |
| PK-A-002 | AR-001 | workspace | atlas-west-overlay | experiments[id=exp-overlay].artifacts.public_read | false | | 1 | yes | | | |

## Retention Class Lattice

| class | rank |
| ----- | ---- |
| standard-90d | 10 |

## Credential Reference Map

| uri_prefix | username | cred_ref | match_mode |
| ---------- | -------- | -------- | ---------- |
| https://track.atlasbench.internal | admin | OVERLAY_TOKEN | longest_prefix |
