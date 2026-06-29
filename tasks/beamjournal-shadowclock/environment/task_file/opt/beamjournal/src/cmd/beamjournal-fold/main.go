package main

import (
	"encoding/binary"
	"fmt"
	"os"
)

func main() {
	if len(os.Args) != 4 {
		fmt.Fprintln(os.Stderr, "usage: beamjournal-fold <journal.bin> <fold.plan> <scope>")
		os.Exit(2)
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		panic(err)
	}
	scope := os.Args[3]
	if len(data) < 4 {
		return
	}
	limit := len(data) - 4
	out := make([]byte, 0, len(data))
	for off := 0; off < limit; {
		if off+4 > limit {
			os.Exit(1)
		}
		size := int(binary.LittleEndian.Uint16(data[off:]))
		off += 2
		enabled := data[off]
		off++
		scopeLen := int(data[off])
		off++
		if off+scopeLen+1+size > limit {
			os.Exit(1)
		}
		recScope := string(data[off : off+scopeLen])
		off += scopeLen
		kind := data[off]
		off++
		payload := append([]byte(nil), data[off:off+size]...)
		off += size
		if enabled == 0 || recScope != scope {
			continue
		}
		if kind == 1 {
			for l, r := 0, len(payload)-1; l < r; l, r = l+1, r-1 {
				payload[l], payload[r] = payload[r], payload[l]
			}
		}
		out = append(out, payload...)
	}
	_, _ = os.Stdout.Write(out)
}
