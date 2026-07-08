// Package cli wires the gomvs subcommands to the module proxy client, the
// go.mod parser, the semver ordering and the Minimal Version Selection build
// list. Machine-readable output goes to stdout, one record per line; human
// error detail goes to stderr and a failure exits non-zero.
package cli

import (
	"fmt"
	"os"
	"sort"
	"strings"

	"gomvs/internal/modfile"
	"gomvs/internal/mvs"
	"gomvs/internal/proxy"
	"gomvs/internal/semver"
)

// Run dispatches one invocation and returns the process exit code.
func Run(args []string) int {
	if len(args) < 1 {
		usage()
		return 1
	}
	switch args[0] {
	case "versions":
		return cmdVersions(args[1:])
	case "gomod":
		return cmdGoMod(args[1:])
	case "mvs":
		return cmdMVS(args[1:])
	case "resolve":
		return cmdResolve(args[1:])
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", args[0])
		usage()
		return 1
	}
}

func usage() {
	fmt.Fprint(os.Stderr, `gomvs - query the Go module proxy and resolve dependencies by MVS

Usage:
  gomvs versions <module>
  gomvs gomod <module> <version>
  gomvs mvs <module> <version>
  gomvs resolve <module> <version> <dep>
`)
}

// fetcher adapts the proxy client to the mvs.ModFetcher interface by fetching
// and parsing a module's go.mod.
type fetcher struct{ c *proxy.Client }

func (f fetcher) Mod(module, version string) (*modfile.File, error) {
	body, err := f.c.GoMod(module, version)
	if err != nil {
		return nil, err
	}
	return modfile.Parse(body)
}

func cmdVersions(args []string) int {
	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "usage: gomvs versions <module>")
		return 1
	}
	c := proxy.New()
	body, err := c.List(args[0])
	if err != nil {
		return fail(err)
	}
	var vs []semver.Version
	for _, line := range strings.Split(string(body), "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		v, err := semver.Parse(line)
		if err != nil {
			return fail(err)
		}
		vs = append(vs, v)
	}
	semver.Sort(vs)
	for _, v := range vs {
		fmt.Println(v.String())
	}
	return 0
}

func cmdGoMod(args []string) int {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: gomvs gomod <module> <version>")
		return 1
	}
	c := proxy.New()
	body, err := c.GoMod(args[0], args[1])
	if err != nil {
		return fail(err)
	}
	mf, err := modfile.Parse(body)
	if err != nil {
		return fail(err)
	}
	fmt.Printf("module %s\n", mf.Path)
	if mf.Go == "" {
		fmt.Println("go none")
	} else {
		fmt.Printf("go %s\n", mf.Go)
	}
	reqs := append([]modfile.Require(nil), mf.Requires...)
	sort.Slice(reqs, func(i, j int) bool { return reqs[i].Path < reqs[j].Path })
	for _, r := range reqs {
		fmt.Printf("require %s %s\n", r.Path, r.Version)
	}
	excl := append([]modfile.Exclude(nil), mf.Excludes...)
	sort.Slice(excl, func(i, j int) bool {
		if excl[i].Path != excl[j].Path {
			return excl[i].Path < excl[j].Path
		}
		return excl[i].Version < excl[j].Version
	})
	for _, e := range excl {
		fmt.Printf("exclude %s %s\n", e.Path, e.Version)
	}
	repl := append([]modfile.Replace(nil), mf.Replaces...)
	sort.Slice(repl, func(i, j int) bool {
		if repl[i].OldPath != repl[j].OldPath {
			return repl[i].OldPath < repl[j].OldPath
		}
		return repl[i].OldVersion < repl[j].OldVersion
	})
	for _, r := range repl {
		if r.OldVersion == "" {
			fmt.Printf("replace %s => %s %s\n", r.OldPath, r.NewPath, r.NewVersion)
		} else {
			fmt.Printf("replace %s %s => %s %s\n", r.OldPath, r.OldVersion, r.NewPath, r.NewVersion)
		}
	}
	return 0
}

func cmdMVS(args []string) int {
	if len(args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: gomvs mvs <module> <version>")
		return 1
	}
	list, err := mvs.BuildList(args[0], args[1], fetcher{proxy.New()})
	if err != nil {
		return fail(err)
	}
	for _, s := range list {
		fmt.Printf("%s %s\n", s.Path, s.Version)
	}
	return 0
}

func cmdResolve(args []string) int {
	if len(args) < 3 {
		fmt.Fprintln(os.Stderr, "usage: gomvs resolve <module> <version> <dep>")
		return 1
	}
	ver, ok, err := mvs.Resolve(args[0], args[1], args[2], fetcher{proxy.New()})
	if err != nil {
		return fail(err)
	}
	if !ok {
		fmt.Println("not_found")
		return 1
	}
	fmt.Println(ver)
	return 0
}

func fail(err error) int {
	fmt.Fprintln(os.Stderr, err)
	return 1
}
