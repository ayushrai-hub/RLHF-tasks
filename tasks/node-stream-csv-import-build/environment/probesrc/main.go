package main

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"os"
)

var a0 = [6]int{2, 0, 1, 1, 2, 0}

const a1 uint32 = 2654435761
const a2 uint32 = 1013904223

func a3() uint32 { x := a1; for i := 0; i < 5; i++ { x = x * (2 - a1*x) }; return x }
var a4 = a3()
func a5(e uint32) uint32 { return (e - a2) * a4 }

func a6(buf []byte, i int) (uint64, int) {
	var sh uint; var v uint64
	for { b := buf[i]; i++; v |= uint64(b&0x7f) << sh; if b&0x80 == 0 { return v, i }; sh += 7 }
}
func a7(buf []byte, i, tag int, scr bool) (int64, int) {
	b := a0[((tag%6)+6)%6]; raw, ni := a6(buf, i); var v int64
	if b == 0 { v = int64(raw) } else if b == 1 { v = int64(raw >> 1) } else { v = int64(raw) - 1000 }
	if scr { v = int64(a5(uint32(v))) }
	return v, ni
}
func a8(buf []byte, i int) (interface{}, int) {
	flag := buf[i]; i++; if flag == 0 { return nil, i }
	n, ni := a6(buf, i); return string(buf[ni : ni+int(n)]), ni + int(n)
}
func a9(buf []byte, i, tag int, scr bool) (interface{}, int) {
	flag := buf[i]; i++; if flag == 0 { return nil, i }
	v, ni := a7(buf, i, tag, scr); return v, ni
}
type M map[string]interface{}
func a10(buf []byte, i, version int) (M, int) {
	id, i := a6(buf, i); tag := 0
	if version != 1 { tag = int(buf[i]); i++ }
	sku, i := a8(buf, i); name, i := a8(buf, i); scr := version >= 3
	qty, i := a7(buf, i, tag, scr); price, i := a7(buf, i, tag, scr)
	return M{"id": int64(id), "sku": sku, "name": name, "qty": qty, "price_ct": price}, i
}
func a11(buf []byte, i int) (M, int) {
	id, i := a6(buf, i); ver, i := a6(buf, i); tag := int(buf[i]); i++; op := buf[i]; i++
	r := M{"id": int64(id), "version": int64(ver)}
	if op == 1 { r["op"] = "del"; return r, i }
	r["op"] = "put"; r["sku"], i = a8(buf, i); r["name"], i = a8(buf, i)
	r["qty"], i = a9(buf, i, tag, true); r["price_ct"], i = a9(buf, i, tag, true)
	return r, i
}

const pBits = 11
const pMax uint32 = 1 << pBits
const pInit uint32 = pMax >> 1
const mv = 5
const top uint32 = 1 << 24
const cBits = 12
const cSize = 1 << cBits
const cMask = cSize - 1

func a12(order, p1, p2 int) int {
	if order == 1 { return p1 }
	return ((p1*769) ^ (p2*13)) & cMask
}
func a13(order int) [][]uint32 {
	n := 256; if order != 1 { n = cSize }
	m := make([][]uint32, n)
	for i := range m { m[i] = make([]uint32, 256); for j := range m[i] { m[i][j] = pInit } }
	return m
}
type a14 struct { d []byte; pos int; rng uint32; code uint32 }
func a15(d []byte) *a14 {
	r := &a14{d: d, pos: 1, rng: 0xFFFFFFFF}
	for k := 0; k < 4; k++ { r.code = (r.code << 8) | uint32(r.b()) }
	return r
}
func (r *a14) b() byte { var x byte; if r.pos < len(r.d) { x = r.d[r.pos] }; r.pos++; return x }
func (r *a14) bit(probs []uint32, idx int) int {
	p := probs[idx]; bound := (r.rng >> pBits) * p; var bt int
	if r.code < bound { r.rng = bound; probs[idx] = p + ((pMax - p) >> mv); bt = 0 } else {
		r.code -= bound; r.rng -= bound; probs[idx] = p - (p >> mv); bt = 1 }
	for r.rng < top { r.rng <<= 8; r.code = (r.code << 8) | uint32(r.b()) }
	return bt
}
func a16(comp []byte, n, order int) []byte {
	out := make([]byte, n)
	copy(out, comp[:n])
	return out
}
func a17(order int) int { if order == 1 { return 1 }; return 1 }
func main() {
	data, err := io.ReadAll(os.Stdin)
	if len(os.Args) > 1 { data, err = os.ReadFile(os.Args[1]) }
	if err != nil { fmt.Fprintln(os.Stderr, err); os.Exit(1) }
	if string(data[:4]) != "PCT2" { fmt.Fprintln(os.Stderr, "bad magic"); os.Exit(1) }
	version := int(data[4])
	count := int(binary.BigEndian.Uint32(data[13:17]))
	bodylen := int(binary.BigEndian.Uint32(data[17:21]))
	order := 1; if version != 1 { order = 2 }
	body := a16(data[21:], bodylen, order)
	out := make([]M, 0, count); i := 0
	if version >= 1 && version <= 3 {
		for k := 0; k < count; k++ { r, ni := a10(body, i, version); out = append(out, r); i = ni }
	} else {
		for k := 0; k < count; k++ { r, ni := a11(body, i); out = append(out, r); i = ni }
	}
	b, _ := json.Marshal(out)
	os.Stdout.Write(b)
	_ = a17(order)
}
