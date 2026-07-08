package scan

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"example.com/registeraudit/internal/codec"
)

type orderSpec struct {
	Priority []string `json:"priority"`
}

func listMregFiles(dir string) ([]string, error) {
	ents, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	var names []string
	for _, e := range ents {
		if e.IsDir() {
			continue
		}
		if filepath.Ext(e.Name()) == ".mreg" {
			names = append(names, e.Name())
		}
	}
	sort.Strings(names)
	return names, nil
}

func applyOrder(dir string, names []string) []string {
	raw, err := os.ReadFile(filepath.Join(dir, ".mregorder"))
	if err != nil {
		return names
	}
	var spec orderSpec
	if err := json.Unmarshal(raw, &spec); err != nil || len(spec.Priority) == 0 {
		return names
	}
	have := map[string]struct{}{}
	for _, n := range names {
		have[n] = struct{}{}
	}
	ordered := []string{}
	seen := map[string]struct{}{}
	for _, name := range spec.Priority {
		if _, ok := have[name]; !ok {
			continue
		}
		if _, dup := seen[name]; dup {
			continue
		}
		ordered = append(ordered, name)
		seen[name] = struct{}{}
	}
	for _, name := range names {
		if _, ok := seen[name]; ok {
			continue
		}
		ordered = append(ordered, name)
	}
	return ordered
}

func LoadDir(dir string) ([]string, []codec.Frame, int, error) {
	names, err := listMregFiles(dir)
	if err != nil {
		return nil, nil, 0, err
	}
	names = applyOrder(dir, names)
	var frames []codec.Frame
	crcTotal := 0
	for _, n := range names {
		blob, err := os.ReadFile(filepath.Join(dir, n))
		if err != nil {
			return nil, nil, 0, err
		}
		parsed, fails, err := codec.ParseFrames(blob)
		if err != nil {
			return nil, nil, 0, err
		}
		crcTotal += fails
		frames = append(frames, parsed...)
	}
	return names, frames, crcTotal, nil
}

func PartitionCheckpoints(frames []codec.Frame) ([]codec.Frame, int) {
	var kept []codec.Frame
	skips := 0
	for _, fr := range frames {
		if fr.Func == 0x00 {
			skips++
			continue
		}
		kept = append(kept, fr)
	}
	return kept, skips
}

func CollapseSeq(frames []codec.Frame) ([]codec.Frame, int) {
	bySeq := map[uint32]codec.Frame{}
	order := []uint32{}
	for _, fr := range frames {
		if _, seen := bySeq[fr.Seq]; !seen {
			order = append(order, fr.Seq)
		}
		bySeq[fr.Seq] = fr
	}
	var out []codec.Frame
	for _, seq := range order {
		out = append(out, bySeq[seq])
	}
	return out, len(frames) - len(out)
}

func SummarizeRegSpan(frames []codec.Frame) (int, int) {
	minReg, maxReg := 0, 0
	first := true
	for _, fr := range frames {
		if fr.Func != 0x03 {
			continue
		}
		r := int(fr.Reg)
		if first || r < minReg {
			minReg = r
		}
		if r > maxReg {
			maxReg = r
		}
		first = false
	}
	if first {
		return 0, 0
	}
	return minReg, maxReg
}

func LoadSlaveAllowlist(path string) (map[uint8]struct{}, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	out := map[uint8]struct{}{}
	for _, line := range splitLines(string(raw)) {
		if line == "" || line[0] == '#' {
			continue
		}
		var id int
		if _, err := fmt.Sscanf(line, "%d", &id); err != nil {
			continue
		}
		out[uint8(id)] = struct{}{}
	}
	return out, nil
}

func SlaveAllowed(slave uint8, allowed map[uint8]struct{}) bool {
	_, ok := allowed[slave]
	return ok
}

func splitLines(s string) []string {
	var out []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			out = append(out, trimSpace(s[start:i]))
			start = i + 1
		}
	}
	if start < len(s) {
		out = append(out, trimSpace(s[start:]))
	}
	return out
}

func trimSpace(s string) string {
	for len(s) > 0 && (s[0] == ' ' || s[0] == '\t') {
		s = s[1:]
	}
	for len(s) > 0 && (s[len(s)-1] == ' ' || s[len(s)-1] == '\t') {
		s = s[:len(s)-1]
	}
	return s
}
