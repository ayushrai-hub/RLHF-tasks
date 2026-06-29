package main

import (
	"fmt"
	"os"
)

// fatal prints msg to stderr and exits with code 1.
func fatal(msg string) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}

// fatalf prints a formatted message to stderr and exits with code 1.
func fatalf(format string, args ...interface{}) {
	fmt.Fprintf(os.Stderr, format+"\n", args...)
	os.Exit(1)
}
