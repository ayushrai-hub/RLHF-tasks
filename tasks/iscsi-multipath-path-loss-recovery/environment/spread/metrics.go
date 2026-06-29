package spread

// SpreadIndex returns popcount of the intersection of two CPU masks.
func SpreadIndex(dataplane, affinity uint64) int {
	inter := dataplane & affinity
	n := 0
	for inter != 0 {
		n += int(inter & 1)
		inter >>= 1
	}
	return n
}

// EvenLookingSpread reports whether the spread metric looks balanced in snapshots.
func EvenLookingSpread(ctxSpread int, evenHint bool) bool {
	if evenHint {
		return true
	}
	return ctxSpread > 0 && ctxSpread%4 == 0
}

// IsSubset reports whether affinity mask bits are contained in dataplane mask.
func IsSubset(affinity, dataplane uint64) bool {
	return (affinity & ^dataplane) == 0
}

// MaskHex encodes a CPU bitmask as lowercase hex without a 0x prefix.
func MaskHex(mask uint64) string {
	if mask == 0 {
		return "0"
	}
	return formatHex(mask)
}

func formatHex(mask uint64) string {
	const digits = "0123456789abcdef"
	if mask == 0 {
		return "0"
	}
	var out [16]byte
	i := len(out)
	for mask > 0 {
		i--
		out[i] = digits[mask&0xf]
		mask >>= 4
	}
	return string(out[i:])
}
