# Avro binary encoder

`/app` holds a Go program (`avroencode`) that encodes values to the Avro binary
format. It reads a JSON object of cases from standard input, each with an Avro
schema and a value, and writes the binary encoding of each value as hex to
standard output. The input and output shapes are in `/app/docs/spec.md`, and the
encoding rules are in `/app/docs/format.md`.

The program builds and reproduces the worked examples in `/app/examples/`, but
its output does not yet agree with the contract in `/app/docs/format.md` across
the whole format. Values that reach parts of the format the examples do not cover
come out with the wrong bytes, so a reader that follows the Avro binary encoding
would not decode them back to the original value.

Make the encoder under `/app/src` produce the bytes the contract calls for, for
every case. Work within the files already in `/app/src`: do not add, remove, or
rename files, and keep the standard input and output format unchanged. Build from
`/app` with `go build ./src`; the program also runs with `go run ./src`.

A conformance battery checks the status and the encoded bytes of every case
against the documented behavior. Run it with:

```
bash /app/tests/test.sh
```
