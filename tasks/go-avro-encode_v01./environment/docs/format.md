# Avro binary encoding contract

This describes how a value is encoded to bytes against its schema. It follows the
Apache Avro 1.11 binary encoding; where a detail is not spelled out here, that
specification governs. A value is encoded to a flat byte sequence with no framing
or header: the bytes of a composite value are the concatenation of the bytes of
its parts. The program emits the lowercase hex of that byte sequence.

## Primitive types

- `null` encodes to zero bytes.
- `boolean` encodes to one byte: 1 for true, 0 for false.
- `int` and `long` are zig-zag mapped (so small-magnitude and negative values
  stay short) and then written as a variable-length integer, seven bits per
  byte, least significant group first.
- `float` is four bytes, the IEEE 754 single-precision value in little-endian
  order.
- `double` is eight bytes, the IEEE 754 double-precision value in little-endian
  order.
- `bytes` is a `long` byte count followed by the raw bytes.
- `string` is a `long` count of its length in UTF-8 octets, followed by the
  UTF-8 bytes.

## Named and complex types

- `fixed` is exactly its declared `size` in raw bytes, with no length prefix.
- `enum` is a `long` whose value is the zero-based position of the symbol in the
  schema's symbol list.
- `record` is each field value in the order the fields are declared in the
  schema, concatenated, with nothing between them.
- `array` is written as blocks. A non-empty array is a single block: a positive
  `long` item count, then that many encoded items, then a zero-count block (a
  single zero byte). An empty array is just the zero-count block.
- `map` is written like an array whose items are a string key followed by a
  value. Members are written in ascending order of their UTF-8 key bytes, and the
  block is closed by a zero-count block.
- `union` is a `long` branch index (zero-based, in the order the branches are
  declared in the schema), followed by the value encoded against that branch.

## Conformance

A value that does not match its schema (a wrong JSON kind, an enum symbol that is
not declared, a union branch that is not present, a fixed value of the wrong
size, or an invalid hex string) makes the case an error rather than producing
bytes.

## Worked examples

`environment/examples/` holds input/output pairs covering a record of integers, a
string, a bytes value, an enum, and a nested record. They are a subset of the
contract; the full set of types is described above.
