package main

import (
	"flag"
	"fmt"
	"os"

	"breach-ledger/internal/app"
)

func main() {
	bundle := flag.String("bundle", "", "incident bundle path")
	output := flag.String("output", "", "output directory")
	flag.Parse()
	if *bundle == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "usage: breach-ledger --bundle DIR --output DIR")
		os.Exit(2)
	}
	if err := app.Run(*bundle, *output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
