# Marrow

Marrow is a small, self-contained **lossless data-compression codec**. It
compresses a file with LZ77 (sliding-window back-references) followed by a
single canonical Huffman code, packs the result into a tidy container guarded by
a CRC-32, and decompresses it back to the exact original bytes.

The whole codec is integer and bit work — no platform libraries decide the
output — so a given input always produces the same container, and the format is
simple enough that a second implementation can interoperate with it byte for
byte.

## Build

```
javac -d out src/marrow/*.java
```

Run the CLI with `java -cp out marrow.Main <command>`.

## Commands

```
marrow compress   <in> <out>     # write a Marrow container
marrow decompress <in> <out>     # recover the original from a container
marrow inspect    <file>         # show a container's header
marrow crc        <file>         # CRC-32 of a file
marrow bitprobe                  # round-trip a fixed bit pattern (bit I/O check)
marrow lz         <file>         # the LZ77 token stream
marrow unlz       <tokens> <out> # rebuild bytes from a token listing
marrow huff       <file>         # canonical Huffman code lengths for a file
marrow huffround  <file>         # Huffman encode + decode round-trip
```

Example inputs live in `programs/`.

See `docs/spec.md` for the exact format.
