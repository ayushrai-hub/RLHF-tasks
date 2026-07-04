# AtlasBench MLflow Governance Replay

The offline AtlasBench model lab rebuilds MLflow-style governance state from Markdown policy dossiers and mixed YAML/TOML configuration files. Operators have found that the current `atlas-harden` command can produce different hardened configs and evidence databases depending on config order, stale outputs, duplicate exception rows, and URI credential shapes.

Implement the Go CLI under `/app/atlas-harden` so that it performs a deterministic governance replay from the supplied inputs. You must compute results from the dossier and config files on every run. Static outputs, fixture-specific patches, copied sample outputs, or bypassing the CLI are insufficient.

Build and run from `/app/atlas-harden`:

```bash
go build -o /app/bin/atlas-harden .
/app/bin/atlas-harden \
  --dossier /app/data/governance-dossier.md \
  --config-dir /app/data/configs \
  --out-dir /app/output/configs \
  --evidence /app/output/evidence.db
```

The verifier rebuilds the command, runs it against the bundled inputs, then runs it again against verifier-only valid inputs with new IDs, new model names, extra config files, changed policy rows, and URI variants. The command must exit 0 on valid inputs. It must print a useful error to stderr and exit non-zero when a required input path is missing, when a supported config file is syntactically invalid, when the evidence database cannot be written, or when a required policy table is missing from the dossier.

Re-running on the same inputs must delete stale files under the output config directory, rewrite `/app/output/evidence.db`, and produce byte-identical evidence for byte-identical inputs.

## Inputs

### Config discovery

`--config-dir` may contain files directly under the directory and under one level of subdirectories. Participate only files with suffix `.yaml`, `.yml`, or `.toml`. Use slash-separated relative paths from `--config-dir` as `source_file` values in evidence. Sort participating relative paths lexicographically by raw byte order.

Ignore directories and unsupported suffixes. Do not follow symlinks. Reject any participating file whose relative path contains `..`, an absolute path component, a backslash, or a NUL byte.

The known config basenames are:

- `workspace.toml`
- `experiments.yaml` or `experiments.yml`
- `registry.toml`
- `tracking.yaml` or `tracking.yml`
- optional policy-pack files referenced by `workspace.toml`

Verifier-only inputs may include profile subdirectories such as `profiles/west/experiments.yaml`. Each profile is replayed independently but shares the same dossier. A profile is the directory containing a `workspace.toml`; files in that same directory belong to that profile. Root-level files belong to the root profile.

### `workspace.toml`

Support both dotted TOML keys and nested tables for the same logical paths.

Required logical fields:

- `workspace.id` string
- `workspace.governance.run_id` string, optional; when absent use `default-run`
- `workspace.retention.default_class` string, optional; when absent use `standard-90d`
- `artifacts.public_read` bool, optional; when absent treat as `false`

Optional fields:

- `workspace.governance.profile` string
- `workspace.governance.policy_pack_order` array of strings
- `policy_pack` array entries with `name`, `path`, and optional `enabled`
- `owners.admins` array of strings

A policy pack path is relative to the profile directory. Apply policy-pack rows after dossier rows in the listed order when the pack is enabled. Policy packs use the same Markdown table formats as the dossier. Disabled packs are parsed for syntax only but their rows are not active candidates.

### `experiments.yaml` / `experiments.yml`

The logical root is:

```yaml
experiments:
  - id: exp-alpha
    stage: staging
    owner: team-a
    artifacts:
      public_read: true
      stores:
        - name: primary
          public_read: true
        - name: audit
          public_read: false
    retention:
      override: false
      class: standard-90d
    governance:
      quarantine: false
      labels: [pii-low]
```

Required per experiment:

- `id` string

Optional per experiment:

- `stage` string; default empty string
- `owner` string; default empty string
- `artifacts.public_read` bool; default `false`
- `artifacts.stores[]` list of `{name, public_read}`; absent means no store-level targets
- `retention.override` bool; default `false`
- `retention.class` string; may be absent
- `governance.quarantine` bool; default `false`
- `governance.labels` list of strings; default empty list

### `registry.toml`

Support both nested aliases and dotted alias keys:

```toml
[[models]]
name = "churn-staging"
stage = "staging"
experiment_id = "exp-alpha"
aliases.mutable = true
aliases.production = "v4"
governance.quarantine = false
promotion.locked = false

[[models.alias_history]]
alias = "production"
from_version = "v3"
to_version = "v4"
```

Required per model:

- `name` string

Optional per model:

- `stage` string; default empty string
- `experiment_id` string; default empty string
- `aliases.mutable` bool; default `false`
- `governance.quarantine` bool; default `false`
- `promotion.locked` bool; default `false`
- `alias_history[]` entries; preserve but do not harden directly

### `tracking.yaml` / `tracking.yml`

Support both scalar `tracking.uri` and list `tracking.servers`:

```yaml
tracking:
  uri: "https://admin:secret@track.atlasbench.internal/mlflow"
  servers:
    - name: primary
      uri: "https://admin:secret@track.atlasbench.internal/mlflow"
    - name: shadow
      uri: "https://shadow:secret@shadow.atlasbench.internal/mlflow"
  experiments:
    - id: exp-alpha
      retention:
        override: false
```

Optional logical fields:

- `tracking.uri` string
- `tracking.servers[]` entries with `name` and `uri`
- `tracking.experiments[]` entries with `id` and optional `retention.override` / `retention.class`

If both `tracking.uri` and `tracking.servers[]` are present, harden and record actions for both. The scalar target is `tracking.uri`. Server targets are `tracking.servers[name=<server_name>].uri`.

## Dossier and policy-pack parsing

The dossier and enabled policy packs are Markdown documents. Parse only Markdown pipe tables with exact headers listed below. Ignore fake tables inside fenced code blocks delimited by triple backticks. A table starts at the header row and ends at the first non-pipe row.

Cells may contain escaped pipes as `\|`. The escaped pipe is part of the cell value. Strip one leading and one trailing space around each cell after unescaping `\|`. Do not strip internal spaces.

### Required table: `Active Policy Exceptions`

Header columns, in this exact order:

```text
exception_id | rule_id | scope_class | scope_id | target_path | grant_value | model_allowlist | amendment_seq | active | valid_from_run | valid_until_run | predicate
```

Fields:

- `exception_id`: non-empty string
- `rule_id`: one of `AR-001`, `RM-002`, `TR-003`, `RT-004`, `LG-005`
- `scope_class`: one of `global`, `workspace`, `experiment`, `model`
- `scope_id`: `*` for global, otherwise the workspace ID, experiment ID, or model name
- `target_path`: canonical grammar described below
- `grant_value`: rule-specific string
- `model_allowlist`: comma-separated model names for `RM-002`; empty means none
- `amendment_seq`: non-negative integer
- `active`: `yes` or `no`, case-insensitive
- `valid_from_run`: run ID lower bound, inclusive; empty means no lower bound
- `valid_until_run`: run ID upper bound, exclusive; empty means no upper bound
- `predicate`: optional rule-specific predicate string

Only rows with `active=yes` and whose run window includes the current run ID can become winning candidates. Rows that are inactive or outside the run window are ignored for mutation but must be counted in `exception_resolution` with status `inactive` or `window_miss`.

### Required table: `Credential Reference Map`

Header columns, in this exact order:

```text
uri_prefix | username | cred_ref | match_mode
```

Fields:

- `uri_prefix`: URI prefix without credentials, such as `https://track.atlasbench.internal` or `https://[2001:db8::5]:8443`
- `username`: username to match after URI userinfo percent-decoding
- `cred_ref`: environment credential reference name
- `match_mode`: `exact_host`, `prefix_path`, or `longest_prefix`

Credential map lookup uses matching rows with the same decoded username. If multiple rows match, choose the longest `uri_prefix`; if still tied, choose the row that appears later after dossier and enabled policy packs are concatenated. Preserve the original URI scheme, username spelling, host, port, path, query, and fragment. Replace only the password component with `env:CRED_REF`. Do not double-redact URIs whose password already starts with `env:`.

### Required table: `Retention Class Lattice`

Header columns, in this exact order:

```text
class | rank
```

`rank` is an integer. Higher rank means stricter retention. The effective retention class for an experiment is the class with the highest rank among the workspace default, experiment-level existing class, matching RT-004 exception grants, and any tracking-level existing class, subject to the override rules below.

## Canonical target path grammar

Every evidence `target_path` must use this grammar exactly:

- Workspace artifact public read: `workspace.artifacts.public_read`
- Experiment artifact public read: `experiments[id=<exp_id>].artifacts.public_read`
- Experiment store public read: `experiments[id=<exp_id>].artifacts.stores[name=<store_name>].public_read`
- Model alias mutability: `models[name=<model_name>].aliases.mutable`
- Scalar tracking URI: `tracking.uri`
- Named tracking server URI: `tracking.servers[name=<server_name>].uri`
- Tracking experiment retention class: `experiments[id=<exp_id>].retention.class`
- Model lineage link: `models[name=<model_name>].lineage.experiment_id`

Escape literal `\`, `]`, and `|` characters inside `<exp_id>`, `<store_name>`, `<model_name>`, and `<server_name>` with a leading backslash. Do not quote target IDs. Do not percent-encode target IDs.

Exception rows match target paths after applying the same canonical escaping to config-derived target IDs. Precedence keys on `(rule_id, target_path)` only, not on `exception_id`, `scope_id`, or source document.

## Policy rules

Apply rules in this order for each participating source file:

1. `AR-001`
2. `RM-002`
3. `TR-003`
4. `RT-004`
5. `LG-005`

Within each rule, sort targets by canonical `target_path` ascending. For a given target, record lower-precedence active candidate exceptions as `skipped_conflict` before recording the winning action. Inactive, window-miss, scope-miss, and predicate-miss exception rows are recorded in `exception_resolution`, not as `policy_actions` rows.

### Exception precedence

For active, in-window candidates matching the same `(rule_id, target_path)`, the winner is selected by:

1. higher `scope_class` rank: `experiment` > `model` > `workspace` > `global`
2. higher `amendment_seq`
3. later source document order: dossier first, enabled policy packs in `workspace.governance.policy_pack_order`
4. later row ordinal within that source document

All lower-ranked active candidates for that target are `skipped_conflict` and must not mutate config values.

A candidate has `scope_miss` if its `scope_class` and `scope_id` do not match the current target entity. Scope matching is:

- `global`: `scope_id` must be `*`
- `workspace`: `scope_id` must equal `workspace.id`
- `experiment`: target must be associated with that experiment ID
- `model`: target must be associated with that model name

### AR-001 — Artifact public read

Base value is `false` for:

- `workspace.artifacts.public_read`
- every `experiments[id=...].artifacts.public_read`
- every `experiments[id=...].artifacts.stores[name=...].public_read`

A winning exception may grant `true` or `false`. Mutate the corresponding bool field only when the desired bool differs from the old value. If the field is absent, treat old value as `false`; do not create absent `artifacts.public_read` just to record an already-compliant base value. For store-level targets, create or mutate only the existing store entry being evaluated.

### RM-002 — Registry alias mutability

Base value is `false` for every model `aliases.mutable`.

A winning `RM-002` exception granting `true` applies only if all of the following are true:

- model `stage` is exactly `staging`
- model name is in the exception row `model_allowlist`
- linked experiment exists in the profile's experiments file
- linked experiment is not quarantined
- model `governance.quarantine` is false or absent
- model `promotion.locked` is false or absent
- optional `predicate` is empty or equals `stage=staging`

If a winning exception exists but these grant conditions are not all satisfied, apply base value `false` and record `exception_id` as NULL on the winning `policy_actions` row. Also record an `exception_resolution` row for the candidate with status `predicate_miss` and a reason string naming the first failed condition in this priority order: `stage`, `allowlist`, `experiment_missing`, `experiment_quarantined`, `model_quarantined`, `promotion_locked`, `predicate`.

Support both nested TOML aliases and dotted TOML aliases. Hardened output may normalize dotted aliases to nested TOML tables, but the logical value must be correct.

### TR-003 — Tracking URI credentials

For every scalar or named tracking URI target, detect URI userinfo passwords for `http` and `https` schemes only. Unsupported schemes are already compliant and must not be changed.

If the URI has no password, it is already compliant. If the password starts with `env:`, it is already compliant. If the URI has a password and a credential map row matches, replace only the password with `env:CRED_REF` and record `status=applied`. If no credential map row matches, leave the URI unchanged and record `status=already_compliant` in `policy_actions`, plus an `uri_redactions` row with `status=unmapped_credential`.

URI parsing must preserve:

- original scheme casing normalized to lowercase
- original username spelling
- host, IPv6 brackets, and port
- path
- query string
- fragment

Do not log or store the original plaintext password anywhere except as part of `old_value` in `policy_actions`, because the evidence contract intentionally captures before/after values for replay verification.

### RT-004 — Retention class

Every tracking experiment should have a `retention.class` unless `retention.override=true` and no class exists.

For each tracking experiment target:

- If `retention.override=true` and `retention.class` exists, keep the existing class unless a winning RT-004 exception grants a class with a higher rank in the retention lattice.
- If `retention.override=true` and `retention.class` is absent, do not create a class and do not create a `policy_actions` row for that target.
- If `retention.override` is false or absent, desired class is the highest-ranked class among workspace default, experiments.yaml retention.class for the same experiment ID, tracking existing retention.class, and any winning RT-004 exception grant.
- If a class string is not present in the retention lattice, reject the input as invalid.

`old_value` is the existing tracking retention class, or empty string when absent. `new_value` is the desired class for applied/already-compliant rows.

### LG-005 — Model lineage link

Every registry model with a non-empty `experiment_id` must link to an experiment in the same profile. Emit one `policy_actions` row per model target `models[name=<model_name>].lineage.experiment_id`.

- If the experiment exists and is not quarantined, `new_value` equals the experiment ID and status is `already_compliant`.
- If the experiment is missing, `new_value` is empty, status is `applied`, and the model's `governance.quarantine` must be set to true in output.
- If the experiment exists but is quarantined, `new_value` equals the experiment ID, status is `applied`, and the model's `governance.quarantine` must be set to true in output.

`old_value` is the original `experiment_id` string from the model, or empty string if absent. Do not remove or rewrite `experiment_id`; LG-005 only records lineage and may set model quarantine.

## Output configs

Write hardened configs under `--out-dir` using the same relative path as each participating input config. Delete stale files from previous runs before writing new outputs.

Output serialization must be deterministic:

- YAML uses two-space indentation, block style, UTF-8, trailing newline, and preserves list order from input.
- TOML uses deterministic key order within each table: `workspace`, `artifacts`, `owners`, `policy_pack`, `models`, then unknown tables alphabetically. Within `models`, preserve input model order.
- Unknown fields must be preserved logically. Exact original comments do not need to be preserved.
- Do not write unsupported input files to output.

## Evidence database

Create SQLite at the path passed by `--evidence`. Remove any previous database first. Use exactly these tables and columns.

### `policy_actions`

```sql
CREATE TABLE policy_actions (
  action_id INTEGER PRIMARY KEY,
  source_file TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  old_value TEXT NOT NULL,
  new_value TEXT NOT NULL,
  exception_id TEXT NULL,
  status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  value_digest TEXT NOT NULL
);
```

Allowed `status` values: `applied`, `already_compliant`, `skipped_conflict`.

`reason_code` values:

- `base_policy`
- `winning_exception`
- `lower_precedence_exception`
- `predicate_failed`
- `uri_redacted`
- `uri_already_env`
- `uri_no_password`
- `uri_unmapped`
- `retention_lattice`
- `lineage_ok`
- `lineage_missing_experiment`
- `lineage_quarantined_experiment`

`value_digest` is lowercase SHA-256 hex of:

```text
rule_id + "\x1f" + target_path + "\x1f" + old_value + "\x1f" + new_value + "\x1f" + status + "\n"
```

For bool values, store lowercase `true` or `false`. For absent values, store empty string. For NULL `exception_id`, use SQL NULL, not an empty string.

### `exception_resolution`

```sql
CREATE TABLE exception_resolution (
  resolution_id INTEGER PRIMARY KEY,
  profile_id TEXT NOT NULL,
  source_doc TEXT NOT NULL,
  source_ordinal INTEGER NOT NULL,
  exception_id TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  scope_class TEXT NOT NULL,
  scope_id TEXT NOT NULL,
  amendment_seq INTEGER NOT NULL,
  resolution_status TEXT NOT NULL,
  reason_code TEXT NOT NULL,
  precedence_key TEXT NOT NULL
);
```

Allowed `resolution_status` values: `winner`, `skipped_conflict`, `inactive`, `window_miss`, `scope_miss`, `predicate_miss`.

Record one row for every exception row parsed from the dossier and enabled policy packs for every profile where the row's `rule_id` and `target_path` could be evaluated. `precedence_key` is:

```text
rule_id + "\x1f" + target_path
```

### `uri_redactions`

```sql
CREATE TABLE uri_redactions (
  redaction_id INTEGER PRIMARY KEY,
  source_file TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  target_path TEXT NOT NULL,
  username TEXT NOT NULL,
  uri_prefix TEXT NOT NULL,
  cred_ref TEXT NULL,
  status TEXT NOT NULL
);
```

Allowed `status` values: `redacted`, `already_env`, `no_password`, `unsupported_scheme`, `unmapped_credential`.

### `lineage_edges`

```sql
CREATE TABLE lineage_edges (
  edge_id INTEGER PRIMARY KEY,
  profile_id TEXT NOT NULL,
  model_name TEXT NOT NULL,
  experiment_id TEXT NOT NULL,
  experiment_present INTEGER NOT NULL,
  experiment_quarantined INTEGER NOT NULL,
  model_quarantined_after INTEGER NOT NULL
);
```

Use integer 0/1 for booleans.

### `run_summary`

```sql
CREATE TABLE run_summary (
  dossier_digest TEXT NOT NULL,
  input_configs_digest TEXT NOT NULL,
  output_configs_digest TEXT NOT NULL,
  evidence_chain_digest TEXT NOT NULL,
  profile_count INTEGER NOT NULL,
  action_count INTEGER NOT NULL,
  exception_resolution_count INTEGER NOT NULL,
  uri_redaction_count INTEGER NOT NULL,
  lineage_edge_count INTEGER NOT NULL
);
```

Exactly one row must exist.

Digest rules:

- `dossier_digest`: SHA-256 lowercase hex of raw dossier bytes.
- `input_configs_digest`: recursively sorted participating input relative paths; for each file append `relative_path + "\n" + raw_bytes + "\n"`.
- `output_configs_digest`: same algorithm over output config files.
- `evidence_chain_digest`: iterate `policy_actions` ordered by `action_id`; for each row append all non-digest fields in table column order using `\x1f` as a separator, SQL NULL represented as `<NULL>`, then `\n`; hash the resulting bytes with SHA-256 lowercase hex.

Count fields must equal the actual number of rows in their tables.

## Action ordering

Assign IDs deterministically:

1. Profiles sorted by profile directory path; root profile sorts before subdirectories.
2. Source files within a profile sorted by relative path.
3. Rules in order `AR-001`, `RM-002`, `TR-003`, `RT-004`, `LG-005`.
4. Targets sorted by canonical target path.
5. For one target, `skipped_conflict` policy rows first in loser precedence order from strongest loser to weakest loser, then the winning applied/already-compliant row.

`exception_resolution.resolution_id`, `uri_redactions.redaction_id`, and `lineage_edges.edge_id` use the same profile/source/rule/target traversal whenever applicable.

## Hidden verifier coverage expectations

The verifier may include valid inputs that exercise:

- duplicate `exception_id` values with different amendment sequences
- a higher-ranked exception losing because of a predicate miss
- policy-pack rows overriding dossier rows
- inactive and run-window-miss exception rows
- a fake exception table inside a fenced code block that must be ignored
- escaped pipe characters in table cells
- experiment IDs, model names, and store names containing spaces, `]`, `\`, and `|`
- TOML dotted aliases and nested aliases in the same registry
- tracking URIs with IPv6 hosts, ports, query strings, fragments, already-env passwords, and unsupported schemes
- multiple credential map rows where longest-prefix matching is required
- stale files left in `--out-dir` from a previous run
- profile subdirectories with independent workspace defaults
- missing registry experiment links that trigger LG-005 quarantine
- retention lattice decisions where an exception grant is stricter than workspace default
- byte-identical second runs

Do not depend on the bundled sample IDs or row counts. Compute all outputs from the actual dossier, policy packs, config bytes, and run ID.
