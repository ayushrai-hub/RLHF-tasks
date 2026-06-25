package main

import (
	"errors"
	"flag"
	"fmt"
	"os"

	"example.com/gnvtlv/internal/audit"
	"example.com/gnvtlv/internal/decode"
	"example.com/gnvtlv/internal/policy"
	"example.com/gnvtlv/internal/render"
	"example.com/gnvtlv/internal/resolve"
)

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	sub := os.Args[1]
	args := os.Args[2:]
	var err error
	switch sub {
	case "decode":
		err = runDecode(args)
	case "resolve":
		err = runResolve(args)
	case "audit":
		err = runAudit(args)
	case "-h", "--help", "help":
		usage()
		return
	default:
		fmt.Fprintf(os.Stderr, "unknown subcommand: %s\n", sub)
		usage()
		os.Exit(2)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func usage() {
	fmt.Fprintln(os.Stderr, "usage: gnvtlv {decode|resolve|audit} --in <file> [--policy <path>]")
}

func runDecode(args []string) error {
	fs := flag.NewFlagSet("decode", flag.ExitOnError)
	in := fs.String("in", "", "input Geneve packet file (raw bytes)")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *in == "" {
		return errors.New("decode: --in is required")
	}
	data, err := os.ReadFile(*in)
	if err != nil {
		return err
	}
	d, err := decode.Decode(*in, data)
	if err != nil {
		return err
	}
	return render.WriteJSON(os.Stdout, d)
}

func runResolve(args []string) error {
	fs := flag.NewFlagSet("resolve", flag.ExitOnError)
	in := fs.String("in", "", "input Geneve packet file (raw bytes)")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *in == "" {
		return errors.New("resolve: --in is required")
	}
	data, err := os.ReadFile(*in)
	if err != nil {
		return err
	}
	d, err := decode.Decode(*in, data)
	if err != nil {
		return err
	}
	reg, err := resolve.LoadRegistries(
		"/app/configs/geneve_registry.json",
		"/app/configs/ethertype_registry.json",
	)
	if err != nil {
		return err
	}
	return render.WriteJSON(os.Stdout, resolve.Resolve(d, reg))
}

func runAudit(args []string) error {
	fs := flag.NewFlagSet("audit", flag.ExitOnError)
	in := fs.String("in", "", "input Geneve packet file (raw bytes)")
	pol := fs.String("policy", "/app/configs/audit_policy.json", "policy JSON path")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *in == "" {
		return errors.New("audit: --in is required")
	}
	data, err := os.ReadFile(*in)
	if err != nil {
		return err
	}
	d, err := decode.Decode(*in, data)
	if err != nil {
		return err
	}
	reg, err := resolve.LoadRegistries(
		"/app/configs/geneve_registry.json",
		"/app/configs/ethertype_registry.json",
	)
	if err != nil {
		return err
	}
	r := resolve.Resolve(d, reg)
	p, err := policy.LoadFromFile(*pol)
	if err != nil {
		return err
	}
	return render.WriteJSON(os.Stdout, audit.Audit(d, r, p))
}
