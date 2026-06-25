# docker_network_connectivity_debugger_report.json schema (read-only specification)

Output shape for `/app/build/docker_network_connectivity_debugger_report.json`. Do not edit files under `/app/docs/`.

## finding `operation` field (read first)

| Kinds | `operation` |
|-------|-------------|
| `DNS_UNRESOLVED`, `NETWORK_PARTITION`, `PORT_UNPUBLISHED`, `EGRESS_DENIED`, `ZONE_BLOCKED`, `TLS_REQUIRED` | probe protocol **uppercased** (`TCP`, not `tcp`) |
| `UNKNOWN_CONTAINER` / `UNKNOWN_NETWORK` from `CONNECT_PROBE` steps 1–2 | `""` |
| `BRIDGE_GAP`, `OVERLAY_ASYMMETRY`, `OPEN_DMZ_PATH`, `INSPECT_UNBOUND`, all duplicate/unknown kinds | `""` |

Post-replay audits use `event_seq` = max capture event `seq` plus one per scenario (see DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_RULES.md).

Inputs per `scenario_id` in `/app/data/docker_network_connectivity_debugger_manifest.json`:

- `/app/data/{scenario_id}.json` — scenario defaults only (**must not** contain an `events` array)
- `/app/data/{scenario_id}/docker_network_connectivity_debugger_capture.cnx` — CNX1 capture (`DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_CAPTURE_FORMAT.md`)

Root: `{ "scenarios": [ ... ] }` in manifest order.

Each scenario:

```json
{
  "scenario_id": "docker_network_connectivity_debugger_scenario_01",
  "status": "VALID",
  "duplicate_events_skipped": 0,
  "capture": {
    "format_version": 1,
    "records_total": 5,
    "records_valid": 5,
    "records_rejected": 0,
    "dup_seq_rejects": 0,
    "truncated_tail": 0,
    "payload_bytes": 512
  },
  "egress_rules": [
    {"from_container": "api-edge", "to_container": "billing-svc"}
  ],
  "containers": [
    {
      "container_id": "billing-svc",
      "zone": "internal",
      "labels": ["net:inspect"],
      "published_ports": ["8080/tcp"],
      "connectivity_risk": "none"
    }
  ],
  "findings": []
}
```

Each scenario object keys, in this order only:

`scenario_id`, `status`, `duplicate_events_skipped`, `capture`, `egress_rules`, `containers`, `findings`

Each finding object keys, in this order only:

`finding_id`, `entity_id`, `kind`, `event_seq`, `operation`, `detail`

Each egress rule object keys: `from_container`, `to_container`.

Each container object keys: `container_id`, `zone`, `labels`, `published_ports`, `connectivity_risk`.

## capture object

Only these keys, in this order:

`format_version`, `records_total`, `records_valid`, `records_rejected`, `dup_seq_rejects`, `truncated_tail`, `payload_bytes`

Values come from CNX1 decode per `DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_CAPTURE_FORMAT.md`. `records_total` counts only records whose complete 12-byte header was read.

`egress_rules` sorted by `(from_container, to_container)` ascending.

`containers` sorted by `container_id`. Each container contains only: `container_id`, `zone`, `labels` (sorted array), `published_ports` (sorted array of `"{port}/{protocol}"`), `connectivity_risk` (exactly one of `none`, `elevated`, `critical`; derived **only** from `zone`, never from findings — see DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_RULES.md).

Each finding:

```json
{
  "finding_id": "docker_network_connectivity_debugger_scenario_03::billing-svc::0004",
  "entity_id": "billing-svc",
  "kind": "EGRESS_DENIED",
  "event_seq": 4,
  "operation": "TCP",
  "detail": "api-edge"
}
```

`kind` is exactly one of the kinds listed in DOCKER_NETWORK_CONNECTIVITY_DEBUGGER_RULES.md. `findings` sorted by `finding_id` ascending with stable tie preservation when `finding_id` duplicates occur. Use `[]` never null. `CONNECT_PROBE` steps 3–8 use `operation` = probe protocol **uppercased** (`TCP`, not `tcp`). All other findings, including probe steps 1–2 and post-replay audits, use `operation` = `""`.

Encoding: compact JSON with `separators=(",", ":")` — no space after `:` or `,`. UTF-8, LF line endings, exactly one trailing newline. Go `encoding/json` marshaling of the report structs must emit object keys in the field order listed above (do not use `MarshalIndent` or custom key reordering).

## main.go path literals

`main.go` must contain the full absolute report path `"/app/build/docker_network_connectivity_debugger_report.json"`, the data root `"/app/data"`, and the substrings `docker_network_connectivity_debugger_manifest.json` and `docker_network_connectivity_debugger_capture.cnx` as quoted string literals in source. Do not construct these paths with `filepath.Join` or other helpers.
