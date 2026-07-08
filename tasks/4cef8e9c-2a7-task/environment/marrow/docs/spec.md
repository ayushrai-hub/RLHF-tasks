# Marrow format specification

Marrow is a lossless codec built from LZ77 and a single canonical Huffman code.
This document defines the format exactly enough for an independent
implementation to interoperate with the engine.

## 1. Bit order

Bits are packed **least-significant-bit first**: `write(value, count)` appends the
low `count` bits of `value`, low bit first, and bytes are emitted as they fill.
The final byte is zero-padded. A reader consumes the same stream in the same
order. The single exception is a Huffman code, whose `length` bits are written
**most-significant-bit first** (the natural order for canonical codes) as that
many single-bit writes; the decoder reads them one bit at a time.

## 2. LZ77

The input is parsed left to right into tokens:

- a **literal** is one byte;
- a **match** is `(length, distance)` meaning "copy `length` bytes from
  `distance` bytes before the current output position", with
  `MIN_MATCH = 3 ≤ length ≤ MAX_MATCH = 258` and `1 ≤ distance ≤ WINDOW = 32768`.
  Overlapping copies (distance < length) are allowed and extend byte by byte.

The reference match policy is deterministic: at each position, consider earlier
positions sharing the next three bytes, within the window; take the **longest**
match, breaking ties toward the **nearest** (smallest distance); emit it when it
reaches `MIN_MATCH`, otherwise emit a literal. (A decoder does not need the
policy — only the resulting tokens — so an encoder may choose differently as long
as it emits valid tokens.)

## 3. Symbol alphabet

Tokens are mapped onto 258 symbols:

| symbol    | meaning                                                |
|-----------|--------------------------------------------------------|
| `0..255`  | a literal byte                                         |
| `256`     | end of block (`EOB`)                                    |
| `257`     | a match; raw bits follow (see below)                   |

A block's symbol sequence is the tokens in order, then one `EOB`. After a `257`
symbol, the match parameters are written as raw bits: `length - MIN_MATCH` in
`LEN_BITS = 8` bits, then `distance - 1` in `DIST_BITS = 15` bits.

## 4. Canonical Huffman

Code **lengths** come from a standard Huffman construction over the symbol
frequencies (the block's literals, one count of `257` per match, and one `EOB`).
Ties are broken deterministically: order nodes by weight, then by a stable tag —
the symbol value for a leaf, an increasing counter (starting at 258) for an
internal node. A single used symbol gets length 1.

**Codes** are canonical for those lengths: shorter codes are numerically smaller,
and within a length symbols receive consecutive codes in increasing symbol order.
Formally, with `bl_count[L]` the number of symbols of length `L`,

```
code = 0
for L in 1..maxLen:
    code = (code + bl_count[L-1]) << 1     # first code of length L
    next_code[L] = code
```

and symbols are assigned `next_code[length]++` in increasing symbol order.

## 5. Block

A compressed block is:

```
258 bytes  : the code length of each symbol 0..257 (0 = unused)
bitstream  : the LSB-first packed stream of Huffman codes and raw match bits,
             ending with the EOB code
```

The decoder reads the 258 lengths, rebuilds the identical canonical codes from
them, then decodes symbols until `EOB`, reading the raw length/distance bits
after each `257`, to recover the token stream — so decoding never depends on the
encoder's Huffman tie-breaking.

## 6. Container

```
offset 0  : magic "MRW1"                 (4 bytes)
offset 4  : flag                         (1 byte: 0 stored, 1 compressed)
offset 5  : original size                (4 bytes, big-endian unsigned)
offset 9  : CRC-32 of the original       (4 bytes, big-endian)
offset 13 : payload
```

The CRC-32 is the standard reflected algorithm (polynomial `0xEDB88320`, initial
`0xFFFFFFFF`, final complement). A **compressed** payload is one block; a
**stored** payload is the original bytes verbatim, chosen when the block is not
smaller than the original so the container never grows by more than the 13-byte
header. Decompression rebuilds the bytes and rejects any container whose decoded
length or CRC does not match the header.
