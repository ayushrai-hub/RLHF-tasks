# Output JSON schemas

Every `gnvtlv` subcommand writes pretty-printed JSON to stdout. Object
keys are stable and consumers of this tool diff outputs by line.

## decode

```json
{
  "source": "/app/testdata/two_clean.bin",
  "header": {
    "version": 0,
    "opt_len_words": 5,
    "opt_len_bytes": 20,
    "oam": false,
    "critical": false,
    "reserved6": 0,
    "protocol_type": 25944,
    "vni": 66051,
    "reserved8": 0
  },
  "options": [
    {
      "index": 0,
      "offset_bytes": 8,
      "opt_class": 259,
      "type": 5,
      "critical": false,
      "r_bits": 0,
      "length_words": 1,
      "length_bytes": 4,
      "data_hex": "00000005"
    }
  ],
  "outer_bytes": 28,
  "inner_bytes": 0,
  "errors": []
}
```

## resolve

```json
{
  "source": "/app/testdata/two_clean.bin",
  "header": {
    "version": 0,
    "opt_len_words": 5,
    "opt_len_bytes": 20,
    "oam": false,
    "critical": false,
    "protocol_type": 25944,
    "protocol_type_name": "TransparentEthBridging",
    "vni": 66051
  },
  "options": [
    {
      "index": 0,
      "offset_bytes": 8,
      "opt_class": 259,
      "type": 5,
      "critical": false,
      "length_bytes": 4,
      "name": "ietf-host-id",
      "kind": "u32",
      "recognized": true,
      "decoded": 3405691582,
      "data_hex": "cafebabe"
    }
  ],
  "decode_errors": [],
  "issues": []
}
```

Top-level fields:

| Field           | Type            | Meaning |
|-----------------|-----------------|---------|
| `source`        | string          | the input packet path |
| `header`        | object          | resolved fixed header |
| `options`       | array of object | per-option resolved view |
| `decode_errors` | array of object | verbatim copy of the `errors` array emitted by `decode` for the same input; one entry per strict-decode violation, with the same `{code, where, message, opt_index}` shape |
| `issues`        | array of object | registry-level findings the resolver emits, with shape `{code, opt_index, message}`. The only code defined here is `OPT_LENGTH_MISMATCH`, emitted when a registry entry's `fixed_bytes` does not equal the actual payload `length_bytes` |

Per-option fields added on top of `decode`'s `RawOption`:

| Field        | Type   | Meaning |
|--------------|--------|---------|
| `name`       | string | registry name, or `""` when `recognized=false` |
| `kind`       | string | one of `u32`, `u128`, `struct`, `varbin`, `opaque`, or `unknown` |
| `recognized` | bool   | `true` when the `(opt_class, type)` pair is in the Geneve registry |
| `decoded`    | any    | per-kind decoded value (see below), or `null` when `recognized=false` |

Header field added on top of `decode`'s `Header`:

| Field                | Type   | Meaning |
|----------------------|--------|---------|
| `protocol_type_name` | string | Ethertype registry name, or `""` when not registered |

Per-`kind` shape of the `decoded` field:

| `kind`   | `decoded` shape |
|----------|-----------------|
| `u32`    | JSON integer (big-endian unsigned 32-bit) |
| `u128`   | 32-character lowercase hex string |
| `struct` | object `{"tag": <u32>, "tail_hex": "<lowercase hex of payload bytes 4..>"}` |
| `varbin` | lowercase hex string of the full payload |
| `opaque` | lowercase hex string of the full payload |
| `unknown`| `null` |

Both `decode_errors` and `issues` are always present, even when empty,
and serialise as `[]` rather than `null`.

`recognized=true` means the registry has an entry for the
`(opt_class, type)` pair. `recognized=false` is recorded but is not
itself an error.

## audit

```json
{
  "source": "/app/testdata/unknown_crit.bin",
  "decision": "DROP",
  "override_applied": false,
  "findings": [
    { "opt_index": 0, "code": "UNKNOWN_CRITICAL", "severity": "error",
      "message": "...", "muted": false }
  ],
  "packet_findings": [
    { "code": "UNKNOWN_CRITICAL", "severity": "error",
      "message": "critical+unknown option at index 0 forces DROP per §X.2",
      "muted": false, "override_applied": false }
  ],
  "options_total": 1,
  "options_recognized": 0
}
```

Decision is one of `"ACCEPT"` or `"DROP"` exactly. No other strings
are valid.

## Type constraints

- All integer fields are JSON integers, not floats.
- `outer_bytes`, `inner_bytes`, `length_bytes`, `opt_len_bytes` are
  JSON integers.
- `data_hex` is lowercase hex with no separators.
- Empty arrays serialise as `[]`, never `null`.
