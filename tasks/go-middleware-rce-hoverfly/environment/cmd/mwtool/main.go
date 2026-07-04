package main

import (
	"encoding/json"
	"fmt"
	"os"

	"mwtool/src/service"
)

const adminToken = "admin-token"

func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "usage: mwtool <config.json>")
		os.Exit(2)
	}
	data, err := os.ReadFile(os.Args[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "middleware_config: "+err.Error())
		os.Exit(1)
	}
	var req service.Request
	if err := json.Unmarshal(data, &req); err != nil {
		fmt.Fprintln(os.Stderr, "middleware_config: "+err.Error())
		os.Exit(1)
	}

	svc := service.NewService(req.EnableMiddlewareAPI, adminToken)
	if err := svc.SetMiddleware(req); err != nil {
		fmt.Fprintln(os.Stderr, err.Error())
		os.Exit(1)
	}
	if !svc.HasMiddleware() {
		fmt.Fprintln(os.Stderr, "middleware_state: not set")
		os.Exit(1)
	}
	fmt.Fprintln(os.Stdout, "ok")
}
