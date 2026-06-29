package main

import (
	"fmt"
	"os"

	"nsx/internal/app"
)

func main() {
	if err := app.Dispatch(os.Args[1:]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
