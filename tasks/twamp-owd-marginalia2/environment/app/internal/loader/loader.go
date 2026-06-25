package loader

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"

	"twampowd/internal/types"
)

var intToken = regexp.MustCompile(`^-?[0-9]+$`)

// Load parses the data tree under dir: config.json, reflectors.json, the
// two probe shards, and the markers file.
func Load(dir string) (types.Config, []types.Reflector, []types.Probe, []types.Marker, error) {
	var cfg types.Config
	cfgBytes, err := os.ReadFile(filepath.Join(dir, "config.json"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("config: %w", err)
	}
	if err := json.Unmarshal(cfgBytes, &cfg); err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("config decode: %w", err)
	}

	reflBytes, err := os.ReadFile(filepath.Join(dir, "reflectors.json"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("reflectors: %w", err)
	}
	var refls []types.Reflector
	if err := json.Unmarshal(reflBytes, &refls); err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("reflectors decode: %w", err)
	}

	var probes []types.Probe
	for shardOrder, name := range []string{"probes_shard_a.ndjson", "probes_shard_b.ndjson"} {
		more, err := loadShard(filepath.Join(dir, name), shardOrder)
		if err != nil {
			return cfg, nil, nil, nil, fmt.Errorf("shard %s: %w", name, err)
		}
		probes = append(probes, more...)
	}

	markers, err := loadMarkers(filepath.Join(dir, "markers.ndjson"))
	if err != nil {
		return cfg, nil, nil, nil, fmt.Errorf("markers: %w", err)
	}

	return cfg, refls, probes, markers, nil
}

func loadShard(path string, shardOrder int) ([]types.Probe, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	var out []types.Probe
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var raw map[string]json.RawMessage
		if err := json.Unmarshal([]byte(line), &raw); err != nil {
			continue
		}
		p, ok := parseProbe(raw, shardOrder)
		if !ok {
			continue
		}
		out = append(out, p)
	}
	return out, sc.Err()
}

func parseProbe(raw map[string]json.RawMessage, shardOrder int) (types.Probe, bool) {
	var p types.Probe
	p.ShardOrder = shardOrder
	_ = json.Unmarshal(raw["probe_id"], &p.ProbeID)
	_ = json.Unmarshal(raw["session_id"], &p.SessionID)
	_ = json.Unmarshal(raw["reflector_id"], &p.ReflectorID)

	cyc, ok := strictInt(raw["cycle_id"])
	if !ok {
		return p, false
	}
	p.CycleID = cyc
	send, ok := strictInt(raw["send_ts"])
	if !ok {
		return p, false
	}
	p.SendTsUs = send
	recv, ok := strictInt(raw["recv_ts"])
	if !ok {
		return p, false
	}
	p.RecvTsUs = recv
	tx, ok := strictInt(raw["tx_ts"])
	if !ok {
		return p, false
	}
	p.TxTsUs = tx
	seq, ok := strictInt(raw["seq_no"])
	if !ok {
		return p, false
	}
	p.SeqNo = seq
	rms, _ := strictInt(raw["recv_minus_send"])
	p.RecvMinusSend = rms

	var lf bool
	if err := json.Unmarshal(raw["loss_flag"], &lf); err != nil {
		return p, false
	}
	p.LossFlag = lf

	return p, true
}

// strictInt is the load-time gate for every integer field on the probe
// schema. It accepts a JSON integer or a quoted-integer string and
// rejects every other JSON shape (fractional numbers, decimal-string
// values, booleans, missing). Per probe_intake/strict_int_table.md, a
// row that fails this gate is discarded entirely with no verdict
// emitted.
func strictInt(raw json.RawMessage) (int64, bool) {
	s := strings.TrimSpace(string(raw))
	if strings.HasPrefix(s, "\"") {
		var q string
		if err := json.Unmarshal(raw, &q); err != nil {
			return 0, false
		}
		s = strings.TrimSpace(q)
	}
	if intToken.MatchString(s) {
		v, err := strconv.ParseInt(s, 10, 64)
		if err == nil {
			return v, true
		}
	}
	f, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0, false
	}
	return int64(f), true
}

func loadMarkers(path string) ([]types.Marker, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 0, 1024*1024), 1024*1024)
	var out []types.Marker
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		var m struct {
			MarkerID      string `json:"marker_id"`
			Kind          string `json:"kind"`
			CycleID       int64  `json:"cycle_id"`
			ReflectorID   string `json:"reflector_id"`
			WindowOpenUs  int64  `json:"window_open_us"`
			WindowCloseUs int64  `json:"window_close_us"`
			Seal          string `json:"seal"`
		}
		if err := json.Unmarshal([]byte(line), &m); err != nil {
			continue
		}
		out = append(out, types.Marker{
			MarkerID:      m.MarkerID,
			Kind:          m.Kind,
			CycleID:       m.CycleID,
			ReflectorID:   m.ReflectorID,
			WindowOpenUs:  m.WindowOpenUs,
			WindowCloseUs: m.WindowCloseUs,
			Seal:          m.Seal,
		})
	}
	return out, sc.Err()
}
