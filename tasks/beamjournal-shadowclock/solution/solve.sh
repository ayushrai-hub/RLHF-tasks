#!/usr/bin/env bash
set -euo pipefail

out="/output/beamjournal"
mkdir -p "$out"

cat >"$out/config.term" <<'EOF'
{bind, "127.0.0.1:18444"}.
{journal_path, "/var/lib/beamjournal/journal.bin"}.
{plan_path, "/var/lib/beamjournal/fold.plan"}.
{folder_path, "/usr/local/bin/beamjournal-fold"}.
{epoch, 41}.
EOF

cat >"$out/termrender.go" <<'EOF'
package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

func parseValue(v string) string {
	v = strings.TrimSpace(v)
	v = strings.TrimSuffix(v, ".")
	v = strings.Trim(v, "\"")
	return v
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: beamjournal-termrender <config.term> <out.toml>")
		os.Exit(2)
	}
	values := map[string]string{
		"bind":         "127.0.0.1:18444",
		"journal_path": "/var/lib/beamjournal/journal.bin",
		"plan_path":    "/var/lib/beamjournal/fold.plan",
		"folder_path":  "/usr/local/bin/beamjournal-fold",
		"epoch":        "41",
	}
	f, err := os.Open(os.Args[1])
	if err != nil {
		panic(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if !strings.HasPrefix(line, "{") || !strings.Contains(line, ",") {
			continue
		}
		line = strings.TrimPrefix(line, "{")
		line = strings.TrimSuffix(line, "}.")
		parts := strings.SplitN(line, ",", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		if _, ok := values[key]; ok {
			values[key] = parseValue(parts[1])
		}
	}
	if err := sc.Err(); err != nil {
		panic(err)
	}
	out, err := os.Create(os.Args[2])
	if err != nil {
		panic(err)
	}
	defer out.Close()
	for _, key := range []string{"bind", "journal_path", "plan_path", "folder_path"} {
		fmt.Fprintf(out, "%s = %q\n", key, values[key])
	}
	fmt.Fprintf(out, "epoch = %s\n", values["epoch"])
}
EOF

cat >"$out/journalfold.go" <<'EOF'
package main

import (
	"encoding/binary"
	"fmt"
	"os"
)

type rule struct {
	scope  string
	kind   byte
	action byte
	arg    byte
	window byte
	repeat byte
	salt   byte
	order  int
}

func baseTransform(payload []byte, kind byte) ([]byte, error) {
	out := append([]byte(nil), payload...)
	switch kind {
	case 0:
		return out, nil
	case 1:
		for l, r := 0, len(out)-1; l < r; l, r = l+1, r-1 {
			out[l], out[r] = out[r], out[l]
		}
		return out, nil
	case 2:
		if len(out) > 1 {
			first := out[0]
			copy(out, out[1:])
			out[len(out)-1] = first
		}
		return out, nil
	case 3:
		for i := len(out) - 1; i > 0; i-- {
			out[i] ^= out[i-1]
		}
		return out, nil
	case 4:
		next := make([]byte, 0, len(out))
		for i := 1; i < len(out); i += 2 {
			next = append(next, out[i])
		}
		for i := 0; i < len(out); i += 2 {
			next = append(next, out[i])
		}
		return next, nil
	case 5:
		next := make([]byte, 0, len(out))
		for i := 0; i < len(out); i += 2 {
			if i+1 < len(out) {
				next = append(next, out[i+1], out[i])
			} else {
				next = append(next, out[i])
			}
		}
		return next, nil
	default:
		return nil, fmt.Errorf("bad kind %d", kind)
	}
}

func expandRLE(payload []byte) ([]byte, error) {
	if len(payload)%2 != 0 {
		return nil, fmt.Errorf("odd rle")
	}
	out := []byte{}
	for i := 0; i < len(payload); i += 2 {
		for n := 0; n < int(payload[i]); n++ {
			out = append(out, payload[i+1])
		}
	}
	return out, nil
}

func interleave(payload []byte) []byte {
	firstLen := (len(payload) + 1) / 2
	first := payload[:firstLen]
	second := payload[firstLen:]
	out := make([]byte, 0, len(payload))
	for i := 0; i < firstLen; i++ {
		if i < len(second) {
			out = append(out, second[i])
		}
		out = append(out, first[i])
	}
	return out
}

func rotateLeft(payload []byte, n int) []byte {
	if len(payload) == 0 {
		return payload
	}
	n %= len(payload)
	if n == 0 {
		return payload
	}
	out := append([]byte(nil), payload[n:]...)
	return append(out, payload[:n]...)
}

func rotateRight(payload []byte, n int) []byte {
	if len(payload) == 0 {
		return payload
	}
	n %= len(payload)
	if n == 0 {
		return payload
	}
	out := append([]byte(nil), payload[len(payload)-n:]...)
	return append(out, payload[:len(payload)-n]...)
}

func parsePlan(path string) ([]rule, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(data) < 4 {
		return nil, fmt.Errorf("plan too small")
	}
	limit := len(data) - 4
	out := []rule{}
	for off := 0; off < limit; {
		if data[off] == 255 {
			if off+2 > limit {
				return nil, fmt.Errorf("truncated extended plan")
			}
			scopeLen := int(data[off+1])
			end := off + 2 + scopeLen + 7
			if end > limit {
				return nil, fmt.Errorf("truncated extended plan")
			}
			scope := string(data[off+2 : off+2+scopeLen])
			fields := data[off+2+scopeLen : end]
			if fields[3] != 0 {
				out = append(out, rule{scope: scope, kind: fields[0], action: fields[1], arg: fields[2], window: fields[4], repeat: fields[5], salt: fields[6], order: len(out)})
			}
			off = end
			continue
		}
		scopeLen := int(data[off])
		end := off + 1 + scopeLen + 4
		if end > limit {
			return nil, fmt.Errorf("truncated legacy plan")
		}
		scope := string(data[off+1 : off+1+scopeLen])
		fields := data[off+1+scopeLen : end]
		if fields[3] != 0 {
			out = append(out, rule{scope: scope, kind: fields[0], action: fields[1], arg: fields[2], order: len(out)})
		}
		off = end
	}
	return out, nil
}

func pickRule(rules []rule, scope string, kind byte) *rule {
	var best *rule
	bestSpec := -1
	bestOrder := -1
	for i := range rules {
		r := &rules[i]
		if r.kind != kind || (r.scope != scope && r.scope != "*") {
			continue
		}
		spec := 0
		if r.scope == scope {
			spec = 1
		}
		if spec > bestSpec || (spec == bestSpec && r.order >= bestOrder) {
			best = r
			bestSpec = spec
			bestOrder = r.order
		}
	}
	return best
}

func applyPlan(payload []byte, r *rule) []byte {
	if r == nil || len(payload) == 0 {
		return payload
	}
	switch r.action {
	case 0:
		return payload
	case 1:
		out := append([]byte(nil), payload...)
		for i := range out {
			out[i] ^= r.arg
		}
		return out
	case 2:
		return rotateRight(payload, int(r.arg))
	case 3:
		step := int(r.window)
		if step == 0 {
			step = 1
		}
		keep := int(r.arg) % step
		out := []byte{}
		for i, b := range payload {
			if i%step == keep {
				out = append(out, b)
			}
		}
		return out
	case 4:
		out := append([]byte(nil), payload...)
		for i := 0; i < int(r.repeat); i++ {
			out = append(out, payload[0])
		}
		return append(out, r.salt)
	case 5:
		out := append([]byte(nil), payload...)
		for i := range out {
			out[i] ^= byte(int(r.arg) + int(r.salt) + i*int(r.window))
		}
		return rotateLeft(out, int(r.repeat))
	case 6:
		chunk := int(r.window)
		if chunk == 0 {
			chunk = 1
		}
		out := []byte{}
		for start := 0; start < len(payload); start += chunk {
			end := start + chunk
			if end > len(payload) {
				end = len(payload)
			}
			seen := map[byte]bool{}
			for _, b := range payload[start:end] {
				v := b ^ r.arg
				if !seen[v] {
					seen[v] = true
					out = append(out, v)
				}
			}
		}
		if len(out) > 0 {
			for i := 0; i < int(r.repeat); i++ {
				out = append(out, r.salt)
			}
		}
		return out
	case 7:
		orig := append([]byte(nil), payload...)
		out := append([]byte(nil), payload...)
		for i := 0; i < int(r.repeat); i++ {
			for j := len(orig) - 1; j >= 0; j-- {
				out = append(out, orig[j])
			}
		}
		if r.window != 0 && len(out) > int(r.window) {
			out = out[:int(r.window)]
		}
		mask := r.arg ^ r.salt
		for i := range out {
			out[i] ^= mask
		}
		return out
	default:
		return payload
	}
}

func fold(journalPath, planPath, scope string) ([]byte, int, error) {
	rules, err := parsePlan(planPath)
	if err != nil {
		return nil, 0, err
	}
	data, err := os.ReadFile(journalPath)
	if err != nil {
		return nil, 0, err
	}
	if len(data) < 4 {
		return nil, 0, fmt.Errorf("journal too small")
	}
	limit := len(data) - 4
	out := []byte{}
	entries := 0
	for off := 0; off < limit; {
		if off+4 > limit {
			return nil, 0, fmt.Errorf("truncated journal")
		}
		size := int(binary.LittleEndian.Uint16(data[off:]))
		off += 2
		enabled := data[off]
		off++
		scopeLen := int(data[off])
		off++
		if off+scopeLen+1 > limit {
			return nil, 0, fmt.Errorf("truncated scope")
		}
		recScope := string(data[off : off+scopeLen])
		off += scopeLen
		kind := data[off]
		off++
		if off+size > limit {
			return nil, 0, fmt.Errorf("truncated payload")
		}
		flags := byte(0)
		payload := data[off : off+size]
		if kind == 255 {
			if size < 2 {
				return nil, 0, fmt.Errorf("bad extended record")
			}
			kind = payload[0]
			flags = payload[1]
			payload = payload[2:]
		}
		off += size
		if enabled == 0 || (recScope != scope && recScope != "all") {
			continue
		}
		work := append([]byte(nil), payload...)
		if flags&0x01 != 0 {
			work, err = expandRLE(work)
			if err != nil {
				return nil, 0, err
			}
		}
		if flags&0x02 != 0 {
			work = interleave(work)
		}
		if flags&0x08 != 0 {
			work = append([]byte{byte(int(kind) + len(work))}, append(work, flags)...)
		}
		work, err = baseTransform(work, kind)
		if err != nil {
			return nil, 0, err
		}
		if flags&0x04 != 0 {
			work, err = baseTransform(work, kind)
			if err != nil {
				return nil, 0, err
			}
		}
		work = applyPlan(work, pickRule(rules, scope, kind))
		out = append(out, work...)
		entries++
	}
	return out, entries, nil
}

func main() {
	if len(os.Args) != 4 {
		fmt.Fprintln(os.Stderr, "usage: beamjournal-fold <journal.bin> <fold.plan> <scope>")
		os.Exit(2)
	}
	out, _, err := fold(os.Args[1], os.Args[2], os.Args[3])
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	_, _ = os.Stdout.Write(out)
}
EOF

cat >"$out/main.go" <<'EOF'
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"
)

type config struct {
	Bind        string
	JournalPath string
	PlanPath    string
	FolderPath  string
	Epoch       int
}

func parseConfig(path string) (config, error) {
	cfg := config{Bind: "127.0.0.1:18444", JournalPath: "/var/lib/beamjournal/journal.bin", PlanPath: "/var/lib/beamjournal/fold.plan", FolderPath: "/usr/local/bin/beamjournal-fold", Epoch: 41}
	raw, err := os.ReadFile(path)
	if err != nil {
		return cfg, err
	}
	for _, line := range strings.Split(string(raw), "\n") {
		key, value, ok := strings.Cut(strings.TrimSpace(line), "=")
		if !ok {
			continue
		}
		key = strings.TrimSpace(key)
		value = strings.Trim(strings.TrimSpace(value), "\"")
		switch key {
		case "bind":
			cfg.Bind = value
		case "journal_path":
			cfg.JournalPath = value
		case "plan_path":
			cfg.PlanPath = value
		case "folder_path":
			cfg.FolderPath = value
		case "epoch":
			if n, err := strconv.Atoi(value); err == nil {
				cfg.Epoch = n
			}
		}
	}
	return cfg, nil
}

func countEntries(path, scope string) (int, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, err
	}
	if len(data) < 4 {
		return 0, nil
	}
	count := 0
	limit := len(data) - 4
	for off := 0; off < limit; {
		if off+4 > limit {
			return 0, fmt.Errorf("truncated journal")
		}
		size := int(data[off]) | int(data[off+1])<<8
		off += 2
		enabled := data[off]
		off++
		scopeLen := int(data[off])
		off++
		if off+scopeLen+1 > limit {
			return 0, fmt.Errorf("truncated scope")
		}
		recScope := string(data[off : off+scopeLen])
		off += scopeLen + 1
		if off+size > limit {
			return 0, fmt.Errorf("truncated record")
		}
		off += size
		if enabled != 0 && (recScope == scope || recScope == "all") {
			count++
		}
	}
	return count, nil
}

func main() {
	cfg, err := parseConfig("/etc/beamjournal/service.toml")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		_, _ = io.WriteString(w, "ok\n")
	})
	mux.HandleFunc("/ledger", func(w http.ResponseWriter, r *http.Request) {
		scope := r.URL.Query().Get("scope")
		if scope == "" {
			http.Error(w, "missing scope", http.StatusBadRequest)
			return
		}
		out, err := exec.Command(cfg.FolderPath, cfg.JournalPath, cfg.PlanPath, scope).Output()
		if err != nil {
			http.Error(w, "fold failed", http.StatusInternalServerError)
			return
		}
		entries, err := countEntries(cfg.JournalPath, scope)
		if err != nil {
			http.Error(w, "count failed", http.StatusInternalServerError)
			return
		}
		sum := sha256.Sum256(out)
		resp := struct {
			OK      bool   `json:"ok"`
			Scope   string `json:"scope"`
			Epoch   int    `json:"epoch"`
			Digest  string `json:"digest"`
			Bytes   int    `json:"bytes"`
			Entries int    `json:"entries"`
		}{true, scope, cfg.Epoch, hex.EncodeToString(sum[:]), len(out), entries}
		w.Header().Set("content-type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	})
	srv := &http.Server{Addr: cfg.Bind, Handler: mux, ReadHeaderTimeout: 2 * time.Second}
	if err := srv.ListenAndServe(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
EOF
