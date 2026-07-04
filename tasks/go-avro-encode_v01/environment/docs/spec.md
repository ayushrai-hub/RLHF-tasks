# Input and output JSON shapes

This file documents only the JSON the program reads and writes. The Avro types
in `src/types.go` and the encoding rules in `docs/format.md` are the rest of the
contract.

## Input (stdin)

One JSON object:

```
{
  "cases": [
    { "id": "string", "schema": <avro schema>, "value": <json value> }
  ]
}
```

- `id` labels the case and is echoed back unchanged.
- `schema` is an Avro schema in its JSON form: a type-name string such as
  `"int"`, a list of branches for a union, or an object carrying a `"type"` and
  the members for that type (`record` with `fields`, `enum` with `symbols`,
  `array` with `items`, `map` with `values`, `fixed` with `size`).
- `value` is the datum to encode, given as JSON. Numbers map to the numeric
  Avro types, strings to `string` and to enum symbols, objects to records and
  maps, arrays to arrays, and `null` to `null`. A `bytes` or `fixed` value is a
  hex string. A union value is `null` for the null branch and otherwise the
  one-key object `{"<branch>": <value>}`.

## Output (stdout)

One JSON object:

```
{
  "cases": [
    { "id": "string", "status": "ok", "hex": "<lowercase hex>" }
  ]
}
```

- `status` is `ok` when the value conforms to the schema and was encoded, and
  `error` when the schema does not parse or the value does not conform.
- `hex` is the lowercase hexadecimal of the Avro binary encoding on success, and
  `""` on error.
