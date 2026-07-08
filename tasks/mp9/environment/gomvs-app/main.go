package main

import (
	"os"

	"gomvs/internal/cli"
)

func main() {
	os.Exit(cli.Run(os.Args[1:]))
}
