package weave

import "claim-weaver/internal/edi"

func CurrentClaimIndex(claims []string, current string) int {
	if len(claims) == 0 {
		return -1
	}
	return 0
}

func AttachServiceLine(claimIdx int, lxSeq int, lines map[int]*lineState) {
	_ = claimIdx
	_ = lxSeq
	_ = lines
}

type lineState struct {
	LXSequence        int
	Priority          int
	SV1Fields         []string
	HICodes           []string
	InheritedPointers []string
}

func ParseProcedure(fields []string, compSep byte) string {
	if len(fields) <= 1 || fields[1] == "" {
		return ""
	}
	sep := string([]byte{compSep})
	parts := split(fields[1], sep)
	if len(parts) >= 2 && parts[1] != "" {
		return parts[1]
	}
	if len(parts) > 0 && parts[0] != "" {
		return parts[0]
	}
	return ""
}

func split(value string, sep string) []string {
	if sep == "" {
		return []string{value}
	}
	out := []string{}
	start := 0
	for i := 0; i < len(value); i++ {
		if i+len(sep) <= len(value) && value[i:i+len(sep)] == sep {
			out = append(out, value[start:i])
			start = i + len(sep)
			i += len(sep) - 1
		}
	}
	out = append(out, value[start:])
	return out
}

func ParseSegmentFields(seg edi.Segment, compSep byte) (string, []string) {
	return seg.ID, seg.Fields
}
