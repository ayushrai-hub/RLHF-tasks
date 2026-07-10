package wire

import (
	"encoding/binary"
	"errors"
	"io"
	"os"
)

func W0(path string) ([][]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var frames [][]byte
	for {
		var lenBuf [4]byte
		_, err := io.ReadFull(f, lenBuf[:])
		if err == io.EOF {
			return frames, nil
		}
		if err != nil {
			return nil, err
		}
		n := binary.BigEndian.Uint32(lenBuf[:])
		if n == 0 || n > 1<<20 {
			return nil, errors.New("invalid frame length")
		}
		data := make([]byte, n)
		if _, err := io.ReadFull(f, data); err != nil {
			return nil, err
		}
		frames = append(frames, data)
	}
}
