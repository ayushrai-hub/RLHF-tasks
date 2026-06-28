package main

import (
	"errors"
	"os"

	"example.com/freezeengine"
)

func resolveOutDir() string {
	outDir := "/var/lib/change-freeze/out"
	args := os.Args[1:]
	for i := 0; i < len(args)-1; i++ {
		if args[i] == "--outdir" {
			outDir = args[i+1]
		}
	}
	return outDir
}

func Run() error {
	if len(os.Args) < 2 || os.Args[1] != "compile" {
		return errors.New("usage: change-freeze compile")
	}

	cfg, err := freezeengine.LoadEffectiveConfig("/etc/change-freeze/policy.json", "/etc/change-freeze/policy.d")
	if err != nil {
		return err
	}
	allow, err := freezeengine.LoadAllowlist("/var/spool/change-freeze/inbox/allowlist.txt")
	if err != nil {
		return err
	}
	requests, err := freezeengine.LoadRequests("/var/spool/change-freeze/inbox/requests.ndjson")
	if err != nil {
		return err
	}

	return writeOutput(resolveOutDir(), freezeengine.BuildPlans(cfg, allow, requests))
}
