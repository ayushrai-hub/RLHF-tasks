package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	pack := flag.String("pack", "", "scenario pack id")
	bundleOut := flag.String("bundle-out", "", "gzip output path")
	ledgerOut := flag.String("ledger-out", "", "ledger json output path")
	flag.Parse()
	if *pack == "" || *bundleOut == "" || *ledgerOut == "" {
		fmt.Fprintln(os.Stderr, "usage: drv_q7 --pack ID --bundle-out PATH --ledger-out PATH")
		os.Exit(2)
	}
	if err := runPack(*pack, *bundleOut, *ledgerOut); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
