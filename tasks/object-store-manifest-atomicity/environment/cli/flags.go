package app

import (
	"flag"
	"fmt"
	"io"
)

type pathPair struct {
	store string
	out   string
}

func parseStoreOut(name string, args []string, stderr io.Writer) (pathPair, bool) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(stderr)
	p := pathPair{}
	fs.StringVar(&p.store, "store", "", "store root")
	fs.StringVar(&p.out, "out", "", "output directory")
	if err := fs.Parse(args); err != nil {
		return p, false
	}
	if p.store == "" || p.out == "" {
		fmt.Fprintln(stderr, "--store and --out are required")
		return p, false
	}
	return p, true
}

func parseStoreOnly(name string, args []string, stderr io.Writer) (string, bool) {
	fs := flag.NewFlagSet(name, flag.ContinueOnError)
	fs.SetOutput(stderr)
	store := ""
	fs.StringVar(&store, "store", "", "store root")
	if err := fs.Parse(args); err != nil {
		return "", false
	}
	if store == "" {
		fmt.Fprintln(stderr, "--store is required")
		return "", false
	}
	return store, true
}
