package load

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

// Frame represents a single QUIC ACK frame event parsed from NDJSON.
// Numeric fields are zeroed when TypeInvalid is set (strict-int rejection).
// String fields are preserved regardless.
type Frame struct {
	ConnID       string
	PnSpace      string
	AckTsMs      int64
	PacketNumber int64
	LargestAcked int64
	AckDelayUs   int64
	EcnCt0       int64
	EcnCt1       int64
	EcnCe        int64
	AckEliciting bool
	TypeInvalid  bool
	ShardSeq     int64
	ShardFile    string
}

// Marker represents a control-plane marker event from markers.ndjson.
type Marker struct {
	Source     string
	Kind       string
	Conn       string
	TargetLow  int64
	TargetHigh int64
	IssuedTs   int64
	Hmac8      string
}

// Connection represents a registered connection from connections.ndjson.
type Connection struct {
	ConnID string
	Tier   string
	Urgent bool
}

func decodeLine(line []byte) (map[string]interface{}, error) {
	dec := json.NewDecoder(bytes.NewReader(line))
	dec.UseNumber()
	var raw map[string]interface{}
	if err := dec.Decode(&raw); err != nil {
		return nil, err
	}
	return raw, nil
}

func LoadConnections(dataDir string) ([]Connection, error) {
	path := filepath.Join(dataDir, "connections.ndjson")
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var out []Connection
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		raw, err := decodeLine([]byte(line))
		if err != nil {
			return nil, fmt.Errorf("connections.ndjson: %w", err)
		}
		conn := Connection{}
		if v, ok := raw["conn_id"].(string); ok {
			conn.ConnID = v
		}
		if v, ok := raw["tier"].(string); ok {
			conn.Tier = v
		}
		if v, ok := raw["urgent"]; ok {
			b, ok := v.(bool)
			if !ok {
				return nil, fmt.Errorf("connections: urgent must be real bool")
			}
			conn.Urgent = b
		}
		out = append(out, conn)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

func LoadMarkers(dataDir string) ([]Marker, error) {
	path := filepath.Join(dataDir, "markers.ndjson")
	f, err := os.Open(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, nil
		}
		return nil, err
	}
	defer f.Close()
	var out []Marker
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" {
			continue
		}
		raw, err := decodeLine([]byte(line))
		if err != nil {
			return nil, fmt.Errorf("markers.ndjson: %w", err)
		}
		m := Marker{}
		if v, ok := raw["source"].(string); ok {
			m.Source = v
		}
		if v, ok := raw["kind"].(string); ok {
			m.Kind = v
		}
		if v, ok := raw["conn"].(string); ok {
			m.Conn = v
		}
		if v, ok := raw["hmac8"].(string); ok {
			m.Hmac8 = v
		}
		if v, ok := raw["target_low"]; ok {
			if i, ok := strictInt(v); ok {
				m.TargetLow = i
			}
		}
		if v, ok := raw["target_high"]; ok {
			if i, ok := strictInt(v); ok {
				m.TargetHigh = i
			}
		}
		if v, ok := raw["issued_ts"]; ok {
			if i, ok := strictInt(v); ok {
				m.IssuedTs = i
			}
		}
		out = append(out, m)
	}
	if err := sc.Err(); err != nil {
		return nil, err
	}
	return out, nil
}

// LoadFrames discovers every frames_*.ndjson shard under dataDir and parses each line.
// Shard files are processed in ascending filename order.
func LoadFrames(dataDir string) ([]Frame, error) {
	entries, err := os.ReadDir(dataDir)
	if err != nil {
		return nil, err
	}
	var shards []string
	for _, e := range entries {
		name := e.Name()
		if !strings.HasPrefix(name, "frames_") || !strings.HasSuffix(name, ".ndjson") {
			continue
		}
		shards = append(shards, name)
	}
	sort.Strings(shards)
	var out []Frame
	for _, shard := range shards {
		path := filepath.Join(dataDir, shard)
		f, err := os.Open(path)
		if err != nil {
			return nil, err
		}
		sc := bufio.NewScanner(f)
		sc.Buffer(make([]byte, 1<<20), 1<<20)
		for sc.Scan() {
			line := strings.TrimSpace(sc.Text())
			if line == "" {
				continue
			}
			fr, err := parseFrame(line, shard)
			if err != nil {
				f.Close()
				return nil, fmt.Errorf("%s: %w", shard, err)
			}
			out = append(out, fr)
		}
		f.Close()
		if err := sc.Err(); err != nil {
			return nil, err
		}
	}
	return out, nil
}

func parseFrame(line, shard string) (Frame, error) {
	raw, err := decodeLine([]byte(line))
	if err != nil {
		return Frame{}, err
	}
	fr := Frame{ShardFile: shard}
	if v, ok := raw["conn_id"].(string); ok {
		fr.ConnID = v
	}
	if v, ok := raw["pn_space"].(string); ok {
		fr.PnSpace = v
	}
	if v, ok := raw["shard_seq"]; ok {
		if i, ok := strictInt(v); ok {
			fr.ShardSeq = i
		}
	}
	// ack_eliciting must be REAL bool. 0/1 → TYPE_INVALID.
	if v, ok := raw["ack_eliciting"]; ok {
		b, ok := v.(bool)
		if !ok {
			fr.TypeInvalid = true
		} else {
			fr.AckEliciting = b
		}
	} else {
		fr.TypeInvalid = true
	}
	numericKeys := []string{"ack_ts_ms", "packet_number", "largest_acked", "ack_delay_us", "ecn_ct0", "ecn_ct1", "ecn_ce"}
	vals := make(map[string]int64, len(numericKeys))
	for _, k := range numericKeys {
		v, ok := raw[k]
		if !ok {
			fr.TypeInvalid = true
			continue
		}
		i, ok := strictInt(v)
		if !ok {
			fr.TypeInvalid = true
			continue
		}
		vals[k] = i
	}
	if fr.TypeInvalid {
		// Zero all six numerics. Strings preserved.
		fr.AckTsMs, fr.PacketNumber, fr.LargestAcked = 0, 0, 0
		fr.AckDelayUs, fr.EcnCt0, fr.EcnCt1, fr.EcnCe = 0, 0, 0, 0
		fr.AckEliciting = false
		return fr, nil
	}
	fr.AckTsMs = vals["ack_ts_ms"]
	fr.PacketNumber = vals["packet_number"]
	fr.LargestAcked = vals["largest_acked"]
	fr.AckDelayUs = vals["ack_delay_us"]
	fr.EcnCt0 = vals["ecn_ct0"]
	fr.EcnCt1 = vals["ecn_ct1"]
	fr.EcnCe = vals["ecn_ce"]
	return fr, nil
}

// strictInt accepts: JSON integers (json.Number without '.'/'e'/'E') and quoted-int
// strings ("42"). Rejects floats (42.0), decimal strings ("42.5"), bools, null.
func strictInt(v interface{}) (int64, bool) {
	switch x := v.(type) {
	case json.Number:
		s := string(x)
		for _, r := range s {
			if r == '.' || r == 'e' || r == 'E' {
				return 0, false
			}
		}
		n, err := strconv.ParseInt(s, 10, 64)
		if err != nil {
			return 0, false
		}
		return n, true
	case string:
		if x == "" {
			return 0, false
		}
		for _, r := range x {
			if r == '.' || r == 'e' || r == 'E' {
				return 0, false
			}
		}
		n, err := strconv.ParseInt(x, 10, 64)
		if err != nil {
			return 0, false
		}
		return n, true
	}
	return 0, false
}

// NumSuffixLess compares two IDs by the integer suffix after the leading non-digit prefix.
// "C2" < "C10" < "C11". If a side has no numeric suffix, fall back to lex.
func NumSuffixLess(a, b string) bool {
	pa, na, oka := splitSuffix(a)
	pb, nb, okb := splitSuffix(b)
	if oka && okb {
		if pa != pb {
			return pa < pb
		}
		return na < nb
	}
	return a < b
}

func splitSuffix(s string) (string, int64, bool) {
	idx := -1
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c >= '0' && c <= '9' {
			idx = i
			break
		}
	}
	if idx == -1 {
		return s, 0, false
	}
	prefix := s[:idx]
	digits := s[idx:]
	n, err := strconv.ParseInt(digits, 10, 64)
	if err != nil {
		return s, 0, false
	}
	return prefix, n, true
}

// SortConns returns connection IDs sorted by numeric-suffix asc.
func SortConns(ids []string) []string {
	out := make([]string, len(ids))
	copy(out, ids)
	sort.SliceStable(out, func(i, j int) bool {
		return NumSuffixLess(out[i], out[j])
	})
	return out
}
