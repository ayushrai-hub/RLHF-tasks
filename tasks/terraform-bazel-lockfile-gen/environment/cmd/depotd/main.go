package main

import (
	"net/http"
	"os"
	"path/filepath"
)

func main() {
	root := os.Getenv("ENV_ROOT")
	if root == "" {
		root = "/app/environment"
	}
	payloadPath := filepath.Join(root, "svc_c", "fixtures", "payload.json")
	data, err := os.ReadFile(payloadPath)
	if err != nil {
		panic(err)
	}
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok"))
	})
	mux.HandleFunc("/catalog", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write(data)
	})
	_ = http.ListenAndServe("127.0.0.1:8787", mux)
}
