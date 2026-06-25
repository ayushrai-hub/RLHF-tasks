package main

import (
	"fmt"

	"service-ledger/internal/api"
)

func runServe(args []string) error {
	addr := "127.0.0.1:18080"
	for i := 0; i < len(args); i++ {
		if args[i] == "--addr" && i+1 < len(args) {
			addr = args[i+1]
			i++
		}
	}
	server := api.NewServer()
	fmt.Printf("service-ledger listening on %s\n", addr)
	return server.Listen(addr)
}
