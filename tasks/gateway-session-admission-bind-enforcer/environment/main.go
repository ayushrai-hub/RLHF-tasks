package main

import (
	"encoding/json"
	"fmt"
	"os"

	"gateway-session/session"
)

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: main <session_dir> <request.json>")
		os.Exit(2)
	}

	store, err := session.Open(os.Args[1])
	if err != nil {
		fmt.Fprintf(os.Stderr, "open session: %v\n", err)
		os.Exit(1)
	}
	data, err := os.ReadFile(os.Args[2])
	if err != nil {
		fmt.Fprintf(os.Stderr, "read request: %v\n", err)
		os.Exit(1)
	}
	var req session.Request
	if err := json.Unmarshal(data, &req); err != nil {
		fmt.Fprintf(os.Stderr, "parse request: %v\n", err)
		os.Exit(1)
	}
	if err := session.ValidateRequest(req); err != nil {
		fmt.Fprintf(os.Stderr, "validate request: %v\n", err)
		os.Exit(1)
	}
	store.NormalizeRequest(&req)
	if err := store.ProcessAdmit(req); err != nil {
		fmt.Fprintf(os.Stderr, "admit: %v\n", err)
		os.Exit(1)
	}
	if err := store.Save(); err != nil {
		fmt.Fprintf(os.Stderr, "save: %v\n", err)
		os.Exit(1)
	}
	out, err := session.ExportFromSnapshot(os.Args[1], store)
	if err != nil {
		fmt.Fprintf(os.Stderr, "export: %v\n", err)
		os.Exit(1)
	}
	if err := session.WriteOutput(os.Args[1], out); err != nil {
		fmt.Fprintf(os.Stderr, "write output: %v\n", err)
		os.Exit(1)
	}
	payload, _ := json.MarshalIndent(out, "", "  ")
	fmt.Println(string(payload))
}
