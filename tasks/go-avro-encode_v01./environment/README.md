# avroencode

A command-line Avro binary encoder. It reads one JSON object from standard input
describing a set of cases, each with an Avro schema and a value, and writes one
JSON object to standard output with the Avro binary encoding of each value as
hex.

## Layout

- `src/` the Go package (`package main`). Build it with `go build ./src` from
  this directory, or run it with `go run ./src`.
- `docs/spec.md` the input and output JSON shapes.
- `docs/format.md` the Avro binary encoding rules.
- `examples/` worked input/output pairs.

## Running

```
go run ./src < examples/ex01_record.in.json
```

The program reads `stdin` to end of input and prints the result object to
`stdout`.
