package main

import (
	"fmt"
	"os"

	"localretention/src"
)

func main() {
	if err := src.Run(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
