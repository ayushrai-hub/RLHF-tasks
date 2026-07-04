# RTCM3 framing

Each frame in a capture file is concatenated back-to-back.

## Header

| Offset | Size | Field |
|--------|------|-------|
| 0 | 1 | Preamble `0xD3` |
| 1 | 1 | Reserved (upper 6 bits must be 0) + length bits 9–8 |
| 2 | 1 | Length bits 7–0 |
| 3 | `length` | Payload |
| 3+length | 3 | CRC-24Q big-endian |

`length` is the payload byte count (10-bit value).

## CRC-24Q

Compute CRC over bytes `[0 .. 3+length)` (preamble through end of payload). Polynomial `0x1864CFB`, init `0`, no final XOR. Compare the 24-bit result to the trailing three bytes (big-endian).

## MSM7 synthetic payload (message type 1077)

When the first two payload bytes (big-endian `u16`) equal `1077`, the remainder is an MSM7 synthetic block documented in `msm7-contract.md`.

## Decode rules

1. Walk the capture until EOF.
2. For each frame, parse header and payload length.
3. Verify CRC **before** writing any ledger or staging row for that frame.
4. On CRC or preamble failure, abort the command with non-zero exit and leave no new staging artifacts from that frame.
