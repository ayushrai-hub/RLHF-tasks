package parse

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
	"os"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
)

var (
	ErrBadMagic   = errors.New("invalid shard magic")
	ErrBadVersion = errors.New("unsupported shard version")
	ErrBadCRC     = errors.New("footer crc mismatch")
)

const shardMagic = "GRSH"

// ReadShard parses a .grsh file into metadata and raw events (ticks not drift-corrected).
func ReadShard(path string) (format.ShardMeta, []format.Event, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return format.ShardMeta{}, nil, err
	}
	if len(data) < 21 {
		return format.ShardMeta{}, nil, fmt.Errorf("shard too short")
	}
	if string(data[0:4]) != "GRPL" {
		return format.ShardMeta{}, nil, ErrBadMagic
	}
	if data[4] != 1 {
		return format.ShardMeta{}, nil, ErrBadVersion
	}
	meta := format.ShardMeta{
		ShardID: binary.LittleEndian.Uint32(data[5:9]),
		DriftMs: int32(binary.LittleEndian.Uint32(data[9:13])),
	}
	count := binary.LittleEndian.Uint32(data[13:17])
	off := 17
	events := make([]format.Event, 0, count)
	for i := uint32(0); i < count; i++ {
		if off+12 > len(data)-4 {
			return format.ShardMeta{}, nil, io.ErrUnexpectedEOF
		}
		ev := format.Event{
			ShardID:     meta.ShardID,
			SourceOrder: int(i),
			Seq:         binary.LittleEndian.Uint32(data[off : off+4]),
			Tick:        binary.LittleEndian.Uint32(data[off+4 : off+8]),
			Type:        binary.LittleEndian.Uint16(data[off+8 : off+10]),
		}
		plen := binary.LittleEndian.Uint16(data[off+10 : off+12])
		off += 12
		if off+int(plen) > len(data)-4 {
			return format.ShardMeta{}, nil, io.ErrUnexpectedEOF
		}
		ev.Payload = make([]byte, plen)
		copy(ev.Payload, data[off:off+int(plen)])
		off += int(plen)
		events = append(events, ev)
	}
	stored := binary.LittleEndian.Uint32(data[len(data)-4:])
	if crc32IEEE(data[0 : len(data)-4]) != stored {
		return format.ShardMeta{}, nil, ErrBadCRC
	}
	return meta, events, nil
}

func crc32IEEE(data []byte) uint32 {
	var crc uint32 = 0xffffffff
	for _, b := range data {
		crc ^= uint32(b)
		for i := 0; i < 8; i++ {
			if crc&1 != 0 {
				crc = (crc >> 1) ^ 0xedb88320
			} else {
				crc >>= 1
			}
		}
	}
	return ^crc
}
