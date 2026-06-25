# Geneve wire form (project specification)

This document is the project's reduction of RFC 8926 to the subset
`gnvtlv` works against. Where this document and the RFC disagree, this
document wins.

## §3.4 Fixed header

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Ver|  Opt Len  |O|C|    Rsvd.  |          Protocol Type        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|        Virtual Network Identifier (VNI)       |    Reserved   |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| Field          | Bits | Notes |
|----------------|------|-------|
| Version (Ver)  | 2    | MUST be 0 (C.1) |
| Opt Len        | 6    | option area length in 4-byte words, range 0..63 |
| O (OAM)        | 1    | OAM packet flag |
| C (Critical)   | 1    | packet-level critical bit |
| Reserved6      | 6    | MUST be 0 (C.2) |
| Protocol Type  | 16   | inner-protocol Ethertype |
| VNI            | 24   | virtual network identifier |
| Reserved8      | 8    | MUST be 0 (C.3) |

## §3.5 Per-option TLV

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|          Option Class         |C|    Type     |R|R|R|  Length |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                      Variable-Length Option Data ...          |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

| Field            | Bits | Notes |
|------------------|------|-------|
| Option Class     | 16   | IANA registry value |
| C (Critical)     | 1    | per-option critical bit |
| Type             | 7    | type within the class |
| R                | 3    | reserved; MUST be 0 (C.4) |
| Length           | 5    | payload length in 4-byte words, range 0..31 |

Total option size on the wire is `4 + Length*4` bytes. An option with
`Length=0` is a 4-byte option with no payload.

## Option-class ranges

| Range            | Meaning |
|------------------|---------|
| 0x0000..0x00FF   | Standards-track, IETF-assigned |
| 0x0100..0xFEFF   | Standards-track, IETF-assigned (extended) |
| 0xFF00..0xFFFF   | Experimenter range; first 4 payload bytes are a vendor ID (see §C.6) |

## Inner-protocol payload

The bytes immediately following the option area are the inner-protocol
payload. Their length is `total_packet_bytes - 8 - (OptLenWords * 4)`.
`gnvtlv` does not parse the inner payload; it only reports its byte
length.
