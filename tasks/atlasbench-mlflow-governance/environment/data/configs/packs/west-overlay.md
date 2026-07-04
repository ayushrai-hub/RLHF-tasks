# West region policy overlay

Regional overlay for atlas-west workspace profiles.

## Active Policy Exceptions

| exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate |
| ------------ | ------- | ----------- | -------- | ----------- | ----------- | --------------- | ------------- | ------ | -------------- | --------------- | --------- |
| EX-PACK-001 | AR-001 | workspace | atlas-west | workspace.artifacts.public_read | false | | 1 | yes | | | |

## Retention Class Lattice

| class | rank |
| ----- | ---- |
| standard-90d | 10 |
| extended-365d | 20 |
| archive-7y | 30 |

## Credential Reference Map

| uri_prefix | username | cred_ref | match_mode |
| ---------- | -------- | -------- | ---------- |
| https://track.atlasbench.internal | admin | ATLAS_TRACK_TOKEN | longest_prefix |
