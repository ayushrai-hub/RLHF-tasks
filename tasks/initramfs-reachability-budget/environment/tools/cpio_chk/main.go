package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	gridAllFlag := flag.Bool("grid-all", false, "run all scenario packs")
	bundleOut := flag.String("bundle-out", "", "terminal gzip path")
	ledgerOut := flag.String("ledger-out", "", "terminal ledger path")
	flag.Parse()
	if !*gridAllFlag || *bundleOut == "" || *ledgerOut == "" {
		fmt.Fprintln(os.Stderr, "usage: cpio_chk --grid-all --bundle-out PATH --ledger-out PATH")
		os.Exit(2)
	}
	if err := gridAll(*bundleOut, *ledgerOut); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
