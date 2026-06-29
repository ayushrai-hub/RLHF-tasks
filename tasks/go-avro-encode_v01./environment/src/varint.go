package main

// writeVarint appends the unsigned variable-length encoding of u: seven bits per
// byte, least significant group first, with the high bit set on every byte
// except the last.
func writeVarint(buf *[]byte, u uint64) {
	for u >= 0x80 {
		*buf = append(*buf, byte(u)|0x80)
		u >>= 7
	}
	*buf = append(*buf, byte(u))
}

// writeLong appends an Avro int or long: the value is zig-zag mapped so small
// magnitudes stay short, then written as an unsigned varint.
func writeLong(buf *[]byte, n int64) {
	zz := uint64(n) << 1
	writeVarint(buf, zz)
}
