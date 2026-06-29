package main

import (
	"bufio"
	"fmt"
	"os"
	"strings"
)

func unquote(v string) string {
	v = strings.TrimSpace(v)
	v = strings.TrimSuffix(v, ".")
	v = strings.Trim(v, "\"")
	return v
}

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: beamjournal-termrender <config.term> <out.toml>")
		os.Exit(2)
	}
	values := map[string]string{
		"bind":         "127.0.0.1:18443",
		"journal_path": "/var/lib/beamjournal/journal.bin",
		"plan_path":    "/var/lib/beamjournal/fold.shadow.plan",
		"folder_path":  "/usr/local/bin/beamjournal-fold-legacy",
		"epoch":        "0",
	}
	f, err := os.Open(os.Args[1])
	if err != nil {
		panic(err)
	}
	defer f.Close()
	sc := bufio.NewScanner(f)
	for sc.Scan() {
		line := strings.TrimSpace(sc.Text())
		if !strings.HasPrefix(line, "{") || !strings.Contains(line, ",") {
			continue
		}
		line = strings.TrimPrefix(line, "{")
		line = strings.TrimSuffix(line, "}.")
		parts := strings.SplitN(line, ",", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := unquote(parts[1])
		switch key {
		case "bind", "journal_path":
			values[key] = val
		case "plan_path":
			continue
		case "folder_path":
			continue
		case "epoch":
			continue
		}
	}
	out, err := os.Create(os.Args[2])
	if err != nil {
		panic(err)
	}
	defer out.Close()
	fmt.Fprintf(out, "bind = %q\n", values["bind"])
	fmt.Fprintf(out, "journal_path = %q\n", values["journal_path"])
	fmt.Fprintf(out, "plan_path = %q\n", values["plan_path"])
	fmt.Fprintf(out, "folder_path = %q\n", values["folder_path"])
	fmt.Fprintf(out, "epoch = %s\n", values["epoch"])
}
