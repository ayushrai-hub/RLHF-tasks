# Canonical wire rules (strictness)

Every rule in this file is a strict-decode error code. The decode
package attaches one `decode.Error` per violation. These do not
involve the policy file — they are properties of the wire form
itself.

| Code                  | §   | Trigger |
|-----------------------|-----|---------|
| `VERSION_NONZERO`     | C.1 | fixed-header Ver != 0 |
| `RESERVED6_NONZERO`   | C.2 | fixed-header Rsvd6 bits != 0 |
| `RESERVED8_NONZERO`   | C.3 | fixed-header trailing reserved byte != 0 |
| `OPT_R_BITS_NONZERO`  | C.4 | any per-option R bits != 0 |
| `OPT_HEADER_TRUNC`    | C.5 | option-area tail has 1..3 bytes (cannot hold a 4-byte option header) |
| `OPT_LEN_OVERRUN`     | C.6 | fixed-header `OptLenBytes` exceeds remaining packet length |
| `OPT_PAYLOAD_OVERRUN` | C.7 | a single option's declared payload extends past the option area |

## §C.4 R-bits semantics

The 3 R bits in each option's second-word byte are reserved by the RFC
and MUST be transmitted as zero. Receivers MUST report a violation
when these bits are nonzero. The bit positions are bits 5..7 of
option byte 3 (most significant bits of the byte), with the 5-bit
Length occupying bits 0..4.

## §C.5 Trailing-byte alignment

The option area is sized by `OptLen * 4`, so it is always a multiple
of 4 bytes. Inside the area, every option is `4 + Length*4` bytes,
which is also always a multiple of 4 bytes. Therefore, when walking
options, the remaining option area should either be empty (loop done)
or be at least 4 bytes (next option header). Anything else means the
sender misencoded the packet — emit `OPT_HEADER_TRUNC` and stop.

## §C.6 Experimenter vendor prefix

Options whose `OptClass` is in the experimenter range (0xFF00..0xFFFF)
carry a 4-byte vendor identifier at the start of their payload. The
resolver records the vendor; the auditor checks it against the policy
allowlist.

## Notes

- A bare 8-byte packet (OptLen=0, no inner payload, no options) is a
  valid packet under this specification. The decoder reports an empty
  options array and `inner_bytes=0`.
- An option with `Length=0` is a 4-byte option header carrying zero
  payload bytes. The decoder still records the option.
