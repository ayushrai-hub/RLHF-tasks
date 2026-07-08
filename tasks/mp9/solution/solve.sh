#!/usr/bin/env bash
# Restore the golden gomvs implementation: proxy path escaping, semver
# precedence ordering, the go.mod parser (module/go/require plus replace and
# exclude directives), and the Minimal Version Selection build list that
# honours the main module's replace and exclude. Then build /app/gomvs.
set -euo pipefail
APP_DIR="/app"

cat > "/app/internal/proxy/escape.go" << 'GOEOF'
package proxy

import "strings"

// EscapePath converts a module path or version string into the case-encoded
// form the module proxy addresses it by. Every uppercase ASCII letter is
// replaced by '!' followed by its lowercase form; all other characters are
// left untouched.
func EscapePath(s string) string {
	if !strings.ContainsFunc(s, func(r rune) bool { return r >= 'A' && r <= 'Z' }) {
		return s
	}
	var b strings.Builder
	b.Grow(len(s) + 4)
	for _, r := range s {
		if r >= 'A' && r <= 'Z' {
			b.WriteByte('!')
			b.WriteRune(r - 'A' + 'a')
		} else {
			b.WriteRune(r)
		}
	}
	return b.String()
}
GOEOF

cat > "/app/internal/semver/order.go" << 'GOEOF'
package semver

import (
	"sort"
	"strings"
)

// Compare orders two versions by Go module precedence and returns -1, 0 or 1.
func Compare(a, b Version) int {
	if c := cmpInt(a.Major, b.Major); c != 0 {
		return c
	}
	if c := cmpInt(a.Minor, b.Minor); c != 0 {
		return c
	}
	if c := cmpInt(a.Patch, b.Patch); c != 0 {
		return c
	}
	return cmpPre(a.Pre, b.Pre)
}

func cmpPre(a, b string) int {
	if a == "" && b == "" {
		return 0
	}
	if a == "" {
		return 1
	}
	if b == "" {
		return -1
	}
	af := strings.Split(a, ".")
	bf := strings.Split(b, ".")
	for i := 0; i < len(af) && i < len(bf); i++ {
		if c := cmpIdent(af[i], bf[i]); c != 0 {
			return c
		}
	}
	return cmpInt(len(af), len(bf))
}

func cmpIdent(a, b string) int {
	an, aNum := toNum(a)
	bn, bNum := toNum(b)
	switch {
	case aNum && bNum:
		return cmpInt(an, bn)
	case aNum && !bNum:
		return -1
	case !aNum && bNum:
		return 1
	default:
		return strings.Compare(a, b)
	}
}

func toNum(s string) (int, bool) {
	n := 0
	if s == "" {
		return 0, false
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, false
		}
		n = n*10 + int(r-'0')
	}
	return n, true
}

func cmpInt(a, b int) int {
	switch {
	case a < b:
		return -1
	case a > b:
		return 1
	default:
		return 0
	}
}

// Sort orders a slice of versions ascending in place by module precedence.
func Sort(vs []Version) {
	sort.SliceStable(vs, func(i, j int) bool { return Compare(vs[i], vs[j]) < 0 })
}

// Max returns the greater of two versions by precedence.
func Max(a, b Version) Version {
	if Compare(a, b) >= 0 {
		return a
	}
	return b
}
GOEOF

cat > "/app/internal/modfile/parse.go" << 'GOEOF'
package modfile

import (
	"fmt"
	"strings"
)

// Parse reads the bytes of a go.mod file into a File. It understands the module
// and go directives, require directives in both the single-line and
// parenthesised block forms, and the replace and exclude directives in both
// forms. Full-line and trailing // comments are stripped, except that an
// // indirect marker on a require line is recorded. Paths and versions may be
// double-quoted, as the older dialect wrote them, and the quotes are removed.
func Parse(data []byte) (*File, error) {
	f := &File{}
	block := "" // "", "require", "replace" or "exclude"

	for _, rawLine := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(rawLine)
		if line == "" || strings.HasPrefix(line, "//") {
			continue
		}
		indirect := isIndirect(line)
		code := stripComment(line)
		if code == "" {
			continue
		}

		if block != "" {
			if code == ")" {
				block = ""
				continue
			}
			if err := f.addBlockEntry(block, code, indirect); err != nil {
				return nil, err
			}
			continue
		}

		switch {
		case hasDirective(code, "module"):
			f.Path = unquote(strings.TrimSpace(trimDirective(code, "module")))
		case hasDirective(code, "go"):
			f.Go = strings.TrimSpace(trimDirective(code, "go"))
		case code == "require (" || code == "require(":
			block = "require"
		case code == "replace (" || code == "replace(":
			block = "replace"
		case code == "exclude (" || code == "exclude(":
			block = "exclude"
		case hasDirective(code, "require"):
			r, err := parseRequire(strings.TrimSpace(trimDirective(code, "require")), indirect)
			if err != nil {
				return nil, err
			}
			f.Requires = append(f.Requires, r)
		case hasDirective(code, "replace"):
			rp, err := parseReplace(strings.TrimSpace(trimDirective(code, "replace")))
			if err != nil {
				return nil, err
			}
			f.Replaces = append(f.Replaces, rp)
		case hasDirective(code, "exclude"):
			ex, err := parseExclude(strings.TrimSpace(trimDirective(code, "exclude")))
			if err != nil {
				return nil, err
			}
			f.Excludes = append(f.Excludes, ex)
		}
	}
	if f.Path == "" {
		return nil, fmt.Errorf("go.mod has no module directive")
	}
	return f, nil
}

func (f *File) addBlockEntry(block, code string, indirect bool) error {
	switch block {
	case "require":
		r, err := parseRequire(code, indirect)
		if err != nil {
			return err
		}
		f.Requires = append(f.Requires, r)
	case "replace":
		rp, err := parseReplace(code)
		if err != nil {
			return err
		}
		f.Replaces = append(f.Replaces, rp)
	case "exclude":
		ex, err := parseExclude(code)
		if err != nil {
			return err
		}
		f.Excludes = append(f.Excludes, ex)
	}
	return nil
}

func parseRequire(code string, indirect bool) (Require, error) {
	fields := strings.Fields(code)
	if len(fields) < 2 {
		return Require{}, fmt.Errorf("malformed require %q", code)
	}
	return Require{Path: unquote(fields[0]), Version: unquote(fields[1]), Indirect: indirect}, nil
}

// parseReplace reads "old => new ver" or "old oldver => new ver".
func parseReplace(code string) (Replace, error) {
	i := strings.Index(code, "=>")
	if i < 0 {
		return Replace{}, fmt.Errorf("malformed replace %q", code)
	}
	left := strings.Fields(code[:i])
	right := strings.Fields(code[i+2:])
	if len(left) < 1 || len(right) < 1 {
		return Replace{}, fmt.Errorf("malformed replace %q", code)
	}
	rp := Replace{OldPath: unquote(left[0])}
	if len(left) >= 2 {
		rp.OldVersion = unquote(left[1])
	}
	rp.NewPath = unquote(right[0])
	if len(right) >= 2 {
		rp.NewVersion = unquote(right[1])
	}
	return rp, nil
}

func parseExclude(code string) (Exclude, error) {
	fields := strings.Fields(code)
	if len(fields) < 2 {
		return Exclude{}, fmt.Errorf("malformed exclude %q", code)
	}
	return Exclude{Path: unquote(fields[0]), Version: unquote(fields[1])}, nil
}

func isIndirect(line string) bool {
	i := strings.Index(line, "//")
	if i < 0 {
		return false
	}
	return strings.TrimSpace(line[i+2:]) == "indirect"
}

func stripComment(line string) string {
	if i := strings.Index(line, "//"); i >= 0 {
		line = line[:i]
	}
	return strings.TrimSpace(line)
}

func hasDirective(code, kw string) bool {
	return code == kw || strings.HasPrefix(code, kw+" ") || strings.HasPrefix(code, kw+"\t")
}

func trimDirective(code, kw string) string {
	return strings.TrimPrefix(code, kw)
}

func unquote(s string) string {
	s = strings.TrimSpace(s)
	if len(s) >= 2 && s[0] == '"' && s[len(s)-1] == '"' {
		return s[1 : len(s)-1]
	}
	return s
}
GOEOF

cat > "/app/internal/mvs/build.go" << 'GOEOF'
package mvs

import (
	"sort"

	"gomvs/internal/modfile"
	"gomvs/internal/semver"
)

// BuildList computes the Minimal Version Selection build list for a target
// module pinned at an exact version.
//
// It walks the reachable graph of (module, version) nodes from the target's
// go.mod and selects the maximum required version of each module across the
// whole closure, excluding the target itself and sorting by path.
//
// The main module's own replace and exclude directives are honoured; a
// dependency's replace and exclude directives are not. An exclude on the main
// module drops any requirement on exactly that (path, version) from the graph.
// A replace on the main module rewrites a matched requirement to the
// replacement path and version and takes its go.mod from there: the selected
// version of that module becomes the replacement version even when it is lower
// than what the graph would otherwise pick. The build-list entry stays keyed by
// the original module path.
func BuildList(target, version string, fetch ModFetcher) ([]Selected, error) {
	root, err := fetch.Mod(target, version)
	if err != nil {
		return nil, err
	}

	wildRepl := map[string]modfile.Replace{}  // oldpath -> replace
	exactRepl := map[string]modfile.Replace{} // oldpath@oldver -> replace
	for _, r := range root.Replaces {
		if r.OldVersion == "" {
			wildRepl[r.OldPath] = r
		} else {
			exactRepl[r.OldPath+"@"+r.OldVersion] = r
		}
	}
	excluded := map[string]bool{} // path@ver
	for _, e := range root.Excludes {
		excluded[e.Path+"@"+e.Version] = true
	}

	// replacementFor returns the fetch path, fetch version and effective
	// selected version for a requirement on (path, ver), and whether a replace
	// applied.
	replacementFor := func(path, ver string) (fetchPath, fetchVer, effVer string) {
		if r, ok := exactRepl[path+"@"+ver]; ok {
			return r.NewPath, r.NewVersion, r.NewVersion
		}
		if r, ok := wildRepl[path]; ok {
			return r.NewPath, r.NewVersion, r.NewVersion
		}
		return path, ver, ver
	}

	type node struct{ path, ver string }
	selected := map[string]semver.Version{}
	rawByPath := map[string]string{}
	visited := map[node]bool{}

	consider := func(path, ver string) error {
		if path == target {
			return nil
		}
		if excluded[path+"@"+ver] {
			return nil
		}
		_, _, effVer := replacementFor(path, ver)
		pv, err := semver.Parse(effVer)
		if err != nil {
			return err
		}
		cur, ok := selected[path]
		if !ok || semver.Compare(pv, cur) > 0 {
			selected[path] = pv
			rawByPath[path] = effVer
		}
		return nil
	}

	queue := []node{{target, version}}
	for len(queue) > 0 {
		n := queue[0]
		queue = queue[1:]
		if visited[n] {
			continue
		}
		visited[n] = true

		fp, fv := n.path, n.ver
		if n.path != target {
			fp, fv, _ = replacementFor(n.path, n.ver)
		}
		mf, err := fetch.Mod(fp, fv)
		if err != nil {
			return nil, err
		}
		for _, req := range mf.Requires {
			if excluded[req.Path+"@"+req.Version] {
				continue
			}
			if err := consider(req.Path, req.Version); err != nil {
				return nil, err
			}
			queue = append(queue, node{req.Path, req.Version})
		}
	}

	out := make([]Selected, 0, len(rawByPath))
	for path, raw := range rawByPath {
		out = append(out, Selected{Path: path, Version: raw})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Path < out[j].Path })
	return out, nil
}

// Resolve returns the selected version of dep in the build list of target at
// version, and ok=false when dep is not part of the build list.
func Resolve(target, version, dep string, fetch ModFetcher) (string, bool, error) {
	list, err := BuildList(target, version, fetch)
	if err != nil {
		return "", false, err
	}
	for _, s := range list {
		if s.Path == dep {
			return s.Version, true, nil
		}
	}
	return "", false, nil
}
GOEOF


cd "$APP_DIR"
gofmt -w .
go vet ./...
go build -o /app/gomvs .
echo "Build successful: /app/gomvs"
