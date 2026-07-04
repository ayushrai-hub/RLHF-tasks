# Frame layout

Each `.mreg` file concatenates one or more frames:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | magic `MREG` |
| 4 | 1 | segment id |
| 5 | 1 | profile id |
| 6 | 1 | slave id |
| 7 | 1 | function code (`0x03` read, `0x00` checkpoint, `0x8x` exception) |
| 8 | 2 | register start, big-endian |
| 10 | 2 | register count, big-endian |
| 12 | 4 | sequence id, big-endian |
| 16 | 2 | payload length, big-endian |
| 18 | N | payload bytes |
| 18+N | 2 | Modbus CRC16 (poly 0xA001, init 0xFFFF), little-endian on wire |

CRC covers bytes from magic through payload inclusive.
