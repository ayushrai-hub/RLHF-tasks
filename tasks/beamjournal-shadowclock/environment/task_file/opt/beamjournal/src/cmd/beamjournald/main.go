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
	"sync"
	"time"
)

type config struct {
	Bind        string
	JournalPath string
	PlanPath    string
	FolderPath  string
	Epoch       int
}

var (
	mu    sync.Mutex
	cache = map[string][]byte{}
)

func parseConfig(path string) config {
	cfg := config{
		Bind:        "127.0.0.1:18443",
		JournalPath: "/var/lib/beamjournal/journal.bin",
		PlanPath:    "/var/lib/beamjournal/fold.shadow.plan",
		FolderPath:  "/usr/local/bin/beamjournal-fold-legacy",
		Epoch:       0,
	}
	b, err := os.ReadFile(path)
	if err != nil {
		return cfg
	}
	for _, line := range strings.Split(string(b), "\n") {
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
	return cfg
}

func folded(cfg config, scope string) ([]byte, error) {
	mu.Lock()
	if b := cache[scope]; b != nil {
		cp := append([]byte(nil), b...)
		mu.Unlock()
		return cp, nil
	}
	mu.Unlock()
	out, err := exec.Command(cfg.FolderPath, cfg.JournalPath, cfg.PlanPath, scope).Output()
	if err != nil {
		return nil, err
	}
	mu.Lock()
	cache[scope] = append([]byte(nil), out...)
	mu.Unlock()
	return out, nil
}

func main() {
	cfg := parseConfig("/etc/beamjournal/service.toml")
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
		b, err := folded(cfg, scope)
		if err != nil {
			http.Error(w, "fold failed", http.StatusInternalServerError)
			return
		}
		sum := sha256.Sum256(b)
		resp := map[string]any{
			"ok":      true,
			"scope":   scope,
			"epoch":   cfg.Epoch,
			"digest":  hex.EncodeToString(sum[:]),
			"bytes":   len(b),
			"entries": strings.Count(string(b), "\n"),
			"ts":      time.Now().UnixNano(),
		}
		w.Header().Set("content-type", "application/json")
		_ = json.NewEncoder(w).Encode(resp)
	})
	srv := &http.Server{Addr: cfg.Bind, Handler: mux, ReadHeaderTimeout: 2 * time.Second}
	if err := srv.ListenAndServe(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
