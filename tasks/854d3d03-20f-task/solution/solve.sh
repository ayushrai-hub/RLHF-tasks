#!/usr/bin/env bash
set -euo pipefail

cd /app

# Replace the incomplete plan/graph logic with a correct implementation that
# resolves the transitive closure, performs per-version constraint solving with
# backtracking, and emits a deterministic build plan + Graphviz graph.
cat > /app/main.go <<'GOEOF'
// Command depmap reconstructs container build/dependency order from OCI-style
// spec fixtures by importing them into SQLite and resolving the build graph
// from that database.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

type specPkg struct {
	Name       string   `json:"name"`
	Constraint string   `json:"constraint"`
	Extras     []string `json:"extras"`
}

type spec struct {
	Name          string    `json:"name"`
	Base          string    `json:"base"`
	Packages      []specPkg `json:"packages"`
	Toolchains    []string  `json:"toolchains"`
	RequiresSpecs []string  `json:"requires_specs"`
}

type lockDep struct {
	Name       string `json:"name"`
	Constraint string `json:"constraint"`
}

type provideEntry struct {
	Virtual string `json:"virtual"`
	Version string `json:"version"`
}

type release struct {
	Version   string                       `json:"version"`
	Deps      []lockDep                    `json:"deps"`
	Conflicts []lockDep                    `json:"conflicts"`
	Provides  []provideEntry               `json:"provides"`
	Extras    map[string][]lockDep         `json:"extras"`
}

type lockPkg struct {
	Name     string    `json:"name"`
	Releases []release `json:"releases"`
}

type lockFile struct {
	Packages []lockPkg `json:"packages"`
}

type toolchain struct {
	Name               string    `json:"name"`
	Version            string    `json:"version"`
	RequiresToolchains []string  `json:"requires_toolchains"`
	RequiresPackages   []lockDep `json:"requires_packages"`
}

type tcFile struct {
	Toolchains []toolchain `json:"toolchains"`
}

func sqlEsc(s string) string { return "'" + strings.ReplaceAll(s, "'", "''") + "'" }

func sqlExec(db, stmts string) error {
	cmd := exec.Command("sqlite3", db)
	cmd.Stdin = strings.NewReader(stmts)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("sqlite3 exec: %v: %s", err, stderr.String())
	}
	return nil
}

func sqlQuery(db, query string) ([]map[string]string, error) {
	cmd := exec.Command("sqlite3", "-json", db, query)
	var out, stderr bytes.Buffer
	cmd.Stdout = &out
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return nil, fmt.Errorf("sqlite3 query: %v: %s", err, stderr.String())
	}
	s := strings.TrimSpace(out.String())
	if s == "" {
		return nil, nil
	}
	var raw []map[string]interface{}
	if err := json.Unmarshal([]byte(s), &raw); err != nil {
		return nil, err
	}
	rows := make([]map[string]string, 0, len(raw))
	for _, r := range raw {
		m := map[string]string{}
		for k, v := range r {
			if v == nil {
				m[k] = ""
			} else {
				m[k] = fmt.Sprintf("%v", v)
			}
		}
		rows = append(rows, m)
	}
	return rows, nil
}

const schema = `
CREATE TABLE specs(name TEXT PRIMARY KEY, base TEXT);
CREATE TABLE spec_packages(spec TEXT, package TEXT, ver_constraint TEXT, extras TEXT);
CREATE TABLE spec_toolchains(spec TEXT, toolchain TEXT);
CREATE TABLE spec_ordering(spec TEXT, required_spec TEXT);
CREATE TABLE packages(name TEXT, version TEXT);
CREATE TABLE package_deps(package TEXT, version TEXT, dep TEXT, ver_constraint TEXT);
CREATE TABLE package_conflicts(package TEXT, version TEXT, conflict TEXT, ver_constraint TEXT);
CREATE TABLE package_provides(package TEXT, version TEXT, virtual TEXT, provided_version TEXT);
CREATE TABLE package_extras(package TEXT, version TEXT, extra_name TEXT, dep_name TEXT, dep_constraint TEXT);
CREATE TABLE toolchains(name TEXT PRIMARY KEY, version TEXT);
CREATE TABLE toolchain_req_toolchains(toolchain TEXT, req TEXT);
CREATE TABLE toolchain_req_packages(toolchain TEXT, package TEXT, ver_constraint TEXT);
`

func cmdImport(specsDir, locksFile, tcPath, dbPath string) error {
	_ = os.Remove(dbPath)
	if err := os.MkdirAll(filepath.Dir(dbPath), 0o755); err != nil {
		return err
	}
	if err := sqlExec(dbPath, schema); err != nil {
		return err
	}

	var b strings.Builder
	b.WriteString("BEGIN;\n")

	files, _ := filepath.Glob(filepath.Join(specsDir, "*.json"))
	sort.Strings(files)
	for _, f := range files {
		data, err := os.ReadFile(f)
		if err != nil {
			return err
		}
		var s spec
		if err := json.Unmarshal(data, &s); err != nil {
			return fmt.Errorf("%s: %v", f, err)
		}
		b.WriteString(fmt.Sprintf("INSERT INTO specs VALUES(%s,%s);\n", sqlEsc(s.Name), sqlEsc(s.Base)))
		for _, p := range s.Packages {
			extrasJSON := "NULL"
			if len(p.Extras) > 0 {
				extBytes, _ := json.Marshal(p.Extras)
				extrasJSON = sqlEsc(string(extBytes))
			}
			b.WriteString(fmt.Sprintf("INSERT INTO spec_packages VALUES(%s,%s,%s,%s);\n", sqlEsc(s.Name), sqlEsc(p.Name), sqlEsc(p.Constraint), extrasJSON))
		}
		for _, t := range s.Toolchains {
			b.WriteString(fmt.Sprintf("INSERT INTO spec_toolchains VALUES(%s,%s);\n", sqlEsc(s.Name), sqlEsc(t)))
		}
		for _, req := range s.RequiresSpecs {
			b.WriteString(fmt.Sprintf("INSERT INTO spec_ordering VALUES(%s,%s);\n", sqlEsc(s.Name), sqlEsc(req)))
		}
	}

	data, err := os.ReadFile(locksFile)
	if err != nil {
		return err
	}
	var lf lockFile
	if err := json.Unmarshal(data, &lf); err != nil {
		return err
	}
	for _, p := range lf.Packages {
		for _, rel := range p.Releases {
			b.WriteString(fmt.Sprintf("INSERT INTO packages VALUES(%s,%s);\n", sqlEsc(p.Name), sqlEsc(rel.Version)))
			for _, d := range rel.Deps {
				b.WriteString(fmt.Sprintf("INSERT INTO package_deps VALUES(%s,%s,%s,%s);\n", sqlEsc(p.Name), sqlEsc(rel.Version), sqlEsc(d.Name), sqlEsc(d.Constraint)))
			}
			for _, c := range rel.Conflicts {
				b.WriteString(fmt.Sprintf("INSERT INTO package_conflicts VALUES(%s,%s,%s,%s);\n", sqlEsc(p.Name), sqlEsc(rel.Version), sqlEsc(c.Name), sqlEsc(c.Constraint)))
			}
			for _, pv := range rel.Provides {
				b.WriteString(fmt.Sprintf("INSERT INTO package_provides VALUES(%s,%s,%s,%s);\n", sqlEsc(p.Name), sqlEsc(rel.Version), sqlEsc(pv.Virtual), sqlEsc(pv.Version)))
			}
			for extraName, extraDeps := range rel.Extras {
				for _, ed := range extraDeps {
					b.WriteString(fmt.Sprintf("INSERT INTO package_extras VALUES(%s,%s,%s,%s,%s);\n", sqlEsc(p.Name), sqlEsc(rel.Version), sqlEsc(extraName), sqlEsc(ed.Name), sqlEsc(ed.Constraint)))
				}
			}
		}
	}

	data, err = os.ReadFile(tcPath)
	if err != nil {
		return err
	}
	var tf tcFile
	if err := json.Unmarshal(data, &tf); err != nil {
		return err
	}
	for _, t := range tf.Toolchains {
		b.WriteString(fmt.Sprintf("INSERT INTO toolchains VALUES(%s,%s);\n", sqlEsc(t.Name), sqlEsc(t.Version)))
		for _, r := range t.RequiresToolchains {
			b.WriteString(fmt.Sprintf("INSERT INTO toolchain_req_toolchains VALUES(%s,%s);\n", sqlEsc(t.Name), sqlEsc(r)))
		}
		for _, r := range t.RequiresPackages {
			b.WriteString(fmt.Sprintf("INSERT INTO toolchain_req_packages VALUES(%s,%s,%s);\n", sqlEsc(t.Name), sqlEsc(r.Name), sqlEsc(r.Constraint)))
		}
	}

	b.WriteString("COMMIT;\n")
	return sqlExec(dbPath, b.String())
}

// parseVer splits a version into its epoch and its dotted release components.
// A leading "<N>!" prefix (PEP 440 epoch) is stripped and returned separately;
// the epoch dominates all release-number comparison. Absent a prefix the epoch
// is 0, so ordinary versions are unaffected.
func parseVer(v string) (int, []int) {
	epoch := 0
	if i := strings.Index(v, "!"); i >= 0 {
		if e, err := strconv.Atoi(strings.TrimSpace(v[:i])); err == nil {
			epoch = e
		}
		v = v[i+1:]
	}
	parts := strings.Split(v, ".")
	out := make([]int, len(parts))
	for i, p := range parts {
		n, err := strconv.Atoi(p)
		if err != nil {
			n = 0
		}
		out[i] = n
	}
	return epoch, out
}

func cmpVer(a, b string) int {
	ea, pa := parseVer(a)
	eb, pb := parseVer(b)
	if ea != eb {
		if ea < eb {
			return -1
		}
		return 1
	}
	n := len(pa)
	if len(pb) > n {
		n = len(pb)
	}
	for i := 0; i < n; i++ {
		x, y := 0, 0
		if i < len(pa) {
			x = pa[i]
		}
		if i < len(pb) {
			y = pb[i]
		}
		if x != y {
			if x < y {
				return -1
			}
			return 1
		}
	}
	return 0
}

// compatUpper computes the exclusive upper bound for a ~= constraint spec.
// ~= X.Y   => <(X+1).0    (2-component: increment the major)
// ~= X.Y.Z => <X.(Y+1).0  (3-component: increment the minor)
// Handles arbitrary depths by incrementing the second-to-last component.
func compatUpper(spec string) string {
	parts := strings.Split(strings.TrimSpace(spec), ".")
	if len(parts) < 2 {
		// degenerate: treat as >=spec with no upper bound by returning a very
		// high sentinel — this shouldn't occur in well-formed fixtures.
		return "99999.0.0"
	}
	// increment the second-to-last component
	idx := len(parts) - 2
	n, err := strconv.Atoi(parts[idx])
	if err != nil {
		return "99999.0.0"
	}
	parts[idx] = strconv.Itoa(n + 1)
	// zero out everything after idx
	for i := idx + 1; i < len(parts); i++ {
		parts[i] = "0"
	}
	return strings.Join(parts, ".")
}

// satisfiesTerm evaluates a single operator-and-version term.
func satisfiesTerm(version, term string) bool {
	c := strings.TrimSpace(term)
	switch {
	case c == "" || c == "*":
		return true
	case strings.HasPrefix(c, "~="):
		spec := strings.TrimSpace(c[2:])
		return cmpVer(version, spec) >= 0 && cmpVer(version, compatUpper(spec)) < 0
	case strings.HasPrefix(c, ">="):
		return cmpVer(version, strings.TrimSpace(c[2:])) >= 0
	case strings.HasPrefix(c, "<="):
		return cmpVer(version, strings.TrimSpace(c[2:])) <= 0
	case strings.HasPrefix(c, "=="):
		return cmpVer(version, strings.TrimSpace(c[2:])) == 0
	case strings.HasPrefix(c, "!="):
		return cmpVer(version, strings.TrimSpace(c[2:])) != 0
	case strings.HasPrefix(c, ">"):
		return cmpVer(version, strings.TrimSpace(c[1:])) > 0
	case strings.HasPrefix(c, "<"):
		return cmpVer(version, strings.TrimSpace(c[1:])) < 0
	default:
		return cmpVer(version, c) == 0
	}
}

// satisfies evaluates a full constraint expression. A constraint is one or more
// alternative groups separated by "|"; the version satisfies the constraint if
// it satisfies AT LEAST ONE group. Within a group, the comma-separated terms are
// ANDed together: the version must satisfy EVERY term in that group.
func satisfies(version, constraint string) bool {
	c := strings.TrimSpace(constraint)
	if c == "" || c == "*" {
		return true
	}
	for _, group := range strings.Split(c, "|") {
		ok := true
		for _, term := range strings.Split(group, ",") {
			t := strings.TrimSpace(term)
			if t == "" {
				continue
			}
			if !satisfiesTerm(version, t) {
				ok = false
				break
			}
		}
		if ok {
			return true
		}
	}
	return false
}

// parseConflict splits a conflict constraint that may carry a trailing
// "; when <package> <constraint>" marker into the version constraint applied to
// the conflict target and an optional activation marker. Without a marker the
// conflict is unconditional (existing behavior).
func parseConflict(con string) (verCon, markerPkg, markerCon string) {
	parts := strings.SplitN(con, ";", 2)
	verCon = strings.TrimSpace(parts[0])
	if len(parts) == 2 {
		rest := strings.TrimSpace(strings.TrimPrefix(strings.TrimSpace(parts[1]), "when"))
		fields := strings.SplitN(rest, " ", 2)
		markerPkg = strings.TrimSpace(fields[0])
		if len(fields) == 2 {
			markerCon = strings.TrimSpace(fields[1])
		}
	}
	return
}

// conflictFires reports whether a (possibly conditional) conflict fires against
// targetVer given selection sel. A conflict carrying a "; when P <c>" marker only
// fires while P is selected at a version satisfying <c>; otherwise it is dormant.
func conflictFires(con, targetVer string, sel map[string]string) bool {
	verCon, mPkg, mCon := parseConflict(con)
	if mPkg != "" {
		sv, ok := sel[mPkg]
		if !ok || sv == "" || !satisfies(sv, mCon) {
			return false
		}
	}
	return satisfies(targetVer, verCon)
}

// depActive reports whether a (possibly conditional) dependency actually
// contributes to the closure right now. A dependency's constraint may carry
// the same "; when P <c>" marker used by conflicts: it only applies while P
// is selected at a version meeting <c>, and is dormant (contributes no edge
// and no constraint) otherwise. A dependency with no marker is unconditional.
func depActive(con string, sel map[string]string) bool {
	_, mPkg, mCon := parseConflict(con)
	if mPkg == "" {
		return true
	}
	sv, ok := sel[mPkg]
	return ok && sv != "" && satisfies(sv, mCon)
}

// depVerCon strips a dependency constraint's optional "; when ..." marker,
// returning just the version constraint its target must satisfy.
func depVerCon(con string) string {
	verCon, _, _ := parseConflict(con)
	return verCon
}

type dep struct{ name, con string }

type node struct {
	ID      string
	Type    string
	Name    string
	Version string
	Deps    []string
}

func resolve(dbPath string) ([]*node, error) {
	specsRows, err := sqlQuery(dbPath, "SELECT name FROM specs;")
	if err != nil {
		return nil, err
	}
	spkgRows, _ := sqlQuery(dbPath, "SELECT spec, package, ver_constraint, extras FROM spec_packages;")
	stcRows, _ := sqlQuery(dbPath, "SELECT spec, toolchain FROM spec_toolchains;")
	sordRows, _ := sqlQuery(dbPath, "SELECT spec, required_spec FROM spec_ordering;")
	pkgRows, _ := sqlQuery(dbPath, "SELECT name, version FROM packages;")
	pdepRows, _ := sqlQuery(dbPath, "SELECT package, version, dep, ver_constraint FROM package_deps;")
	pconfRows, _ := sqlQuery(dbPath, "SELECT package, version, conflict, ver_constraint FROM package_conflicts;")
	provRows, _ := sqlQuery(dbPath, "SELECT package, version, virtual, provided_version FROM package_provides;")
	pkgExtrasRows, _ := sqlQuery(dbPath, "SELECT package, version, extra_name, dep_name, dep_constraint FROM package_extras;")
	tcRows, _ := sqlQuery(dbPath, "SELECT name, version FROM toolchains;")
	treqtcRows, _ := sqlQuery(dbPath, "SELECT toolchain, req FROM toolchain_req_toolchains;")
	treqpkgRows, _ := sqlQuery(dbPath, "SELECT toolchain, package, ver_constraint FROM toolchain_req_packages;")

	specNames := map[string]bool{}
	for _, r := range specsRows {
		specNames[r["name"]] = true
	}
	specPkgs := map[string][]dep{}
	// specPkgExtras: spec -> pkg -> []extra_name
	specPkgExtras := map[string]map[string][]string{}
	for _, r := range spkgRows {
		specPkgs[r["spec"]] = append(specPkgs[r["spec"]], dep{r["package"], r["ver_constraint"]})
		if r["extras"] != "" && r["extras"] != "null" {
			var exts []string
			if err := json.Unmarshal([]byte(r["extras"]), &exts); err == nil && len(exts) > 0 {
				if specPkgExtras[r["spec"]] == nil {
					specPkgExtras[r["spec"]] = map[string][]string{}
				}
				specPkgExtras[r["spec"]][r["package"]] = exts
			}
		}
	}
	specTcs := map[string][]string{}
	for _, r := range stcRows {
		specTcs[r["spec"]] = append(specTcs[r["spec"]], r["toolchain"])
	}
	specRequires := map[string][]string{}
	for _, r := range sordRows {
		specRequires[r["spec"]] = append(specRequires[r["spec"]], r["required_spec"])
	}
	pkgVersions := map[string][]string{}
	for _, r := range pkgRows {
		pkgVersions[r["name"]] = append(pkgVersions[r["name"]], r["version"])
	}
	// per-(package,version) deps
	verDeps := map[string]map[string][]dep{} // pkg -> version -> []dep
	for _, r := range pdepRows {
		p, v := r["package"], r["version"]
		if verDeps[p] == nil {
			verDeps[p] = map[string][]dep{}
		}
		verDeps[p][v] = append(verDeps[p][v], dep{r["dep"], r["ver_constraint"]})
	}
	// per-(package,version) conflicts: selecting this release forbids any
	// in-closure package whose chosen version satisfies the conflict constraint.
	verConflicts := map[string]map[string][]dep{} // pkg -> version -> []conflict
	for _, r := range pconfRows {
		p, v := r["package"], r["version"]
		if verConflicts[p] == nil {
			verConflicts[p] = map[string][]dep{}
		}
		verConflicts[p][v] = append(verConflicts[p][v], dep{r["conflict"], r["ver_constraint"]})
	}

	// per-(package,version,extra_name) extra deps from package_extras table
	verExtras := map[string]map[string]map[string][]dep{} // pkg -> ver -> extra_name -> []dep
	for _, r := range pkgExtrasRows {
		p, v, en := r["package"], r["version"], r["extra_name"]
		if verExtras[p] == nil {
			verExtras[p] = map[string]map[string][]dep{}
		}
		if verExtras[p][v] == nil {
			verExtras[p][v] = map[string][]dep{}
		}
		verExtras[p][v][en] = append(verExtras[p][v][en], dep{r["dep_name"], r["dep_constraint"]})
	}

	// virtual package providers: virtualName -> [{pkg, ver, providedVer}]
	type provCand struct{ pkg, ver, providedVer string }
	virtualProviders := map[string][]provCand{} // virtual → candidates
	for _, r := range provRows {
		virtualProviders[r["virtual"]] = append(virtualProviders[r["virtual"]],
			provCand{r["package"], r["version"], r["provided_version"]})
	}
	// isVirtual: a dep name that has no real package entry but has provider records
	isVirtual := func(name string) bool {
		if _, isReal := pkgVersions[name]; isReal {
			return false
		}
		_, hasProv := virtualProviders[name]
		return hasProv
	}

	tcVersion := map[string]string{}
	for _, r := range tcRows {
		tcVersion[r["name"]] = r["version"]
	}
	tcReqTc := map[string][]string{}
	for _, r := range treqtcRows {
		tcReqTc[r["toolchain"]] = append(tcReqTc[r["toolchain"]], r["req"])
	}
	tcReqPkg := map[string][]dep{}
	for _, r := range treqpkgRows {
		tcReqPkg[r["toolchain"]] = append(tcReqPkg[r["toolchain"]], dep{r["package"], r["ver_constraint"]})
	}

	// Required toolchains: transitive closure over requires_toolchains.
	inTc := map[string]bool{}
	var visitTc func(string)
	visitTc = func(name string) {
		if inTc[name] {
			return
		}
		inTc[name] = true
		for _, r := range tcReqTc[name] {
			visitTc(r)
		}
	}
	for s := range specNames {
		for _, t := range specTcs[s] {
			visitTc(t)
		}
	}

	// Closure of package NAMES. A package's dependency names are the union of
	// the dep names across all of its releases (version-independent membership).
	depNamesOf := func(name string) []string {
		seen := map[string]bool{}
		var out []string
		for _, ds := range verDeps[name] {
			for _, d := range ds {
				if !seen[d.name] {
					seen[d.name] = true
					out = append(out, d.name)
				}
			}
		}
		return out
	}
	inPkg := map[string]bool{}
	var visitPkg func(string)
	visitPkg = func(name string) {
		if inPkg[name] {
			return
		}
		if isVirtual(name) {
			return // virtual dep: resolved in pass 2, not a real package
		}
		inPkg[name] = true
		for _, d := range depNamesOf(name) {
			visitPkg(d)
		}
	}
	for s := range specNames {
		for _, p := range specPkgs[s] {
			visitPkg(p.name)
		}
	}
	for tc := range inTc {
		for _, r := range tcReqPkg[tc] {
			visitPkg(r.name)
		}
	}

	// Fixed (root) constraints: from specs and from required toolchains. These
	// apply regardless of which versions get selected.
	rootCons := map[string][]string{}
	addRoot := func(pkg, con string) {
		if isVirtual(pkg) {
			return // virtual names are not real packages; handled in pass 2
		}
		if inPkg[pkg] {
			rootCons[pkg] = append(rootCons[pkg], con)
		}
	}
	for s := range specNames {
		for _, p := range specPkgs[s] {
			addRoot(p.name, p.con)
		}
	}
	for tc := range inTc {
		for _, r := range tcReqPkg[tc] {
			addRoot(r.name, r.con)
		}
	}

	// Closure package names sorted ascending — the variable order for search.
	names := make([]string, 0, len(inPkg))
	for p := range inPkg {
		names = append(names, p)
	}
	sort.Strings(names)

	// Sort each package's versions in descending order so greedy search picks
	// the highest feasible version first, yielding the lexicographically-greatest
	// (by ascending package name) valid assignment without full enumeration.
	for p := range pkgVersions {
		sort.Slice(pkgVersions[p], func(i, j int) bool {
			return cmpVer(pkgVersions[p][i], pkgVersions[p][j]) > 0
		})
	}

	// Build a fast position-lookup so we can check "is package X already assigned?"
	nameIdx := map[string]int{}
	for i, n := range names {
		nameIdx[n] = i
	}

	// Greedy backtracking search: assigns packages in ascending name order, trying
	// highest version first. Prunes branches that violate any checkable constraint
	// early, and returns the first valid complete assignment (which is guaranteed
	// to be the lexicographically greatest because we greedily pick the highest
	// feasible version at each step before backtracking).
	cur := map[string]string{}
	var search func(i int) bool
	search = func(i int) bool {
		if i == len(names) {
			// Leaf: verify the full assignment (catches any constraint we deferred).
			for p, vs := range rootCons {
				for _, c := range vs {
					if !satisfies(cur[p], c) {
						return false
					}
				}
			}
			for _, p := range names {
				for _, d := range verDeps[p][cur[p]] {
					if inPkg[d.name] && depActive(d.con, cur) && !satisfies(cur[d.name], depVerCon(d.con)) {
						return false
					}
				}
				for _, c := range verConflicts[p][cur[p]] {
					if inPkg[c.name] && conflictFires(c.con, cur[c.name], cur) {
						return false
					}
				}
			}
			return true
		}
		name := names[i]
		for _, v := range pkgVersions[name] {
			cur[name] = v
			ok := true
			// Root constraints for this package.
			for _, c := range rootCons[name] {
				if !satisfies(v, c) {
					ok = false
					break
				}
			}
			// Dep constraints from already-assigned packages that target 'name'.
			for j := 0; j < i && ok; j++ {
				pj := names[j]
				for _, d := range verDeps[pj][cur[pj]] {
					if d.name == name && depActive(d.con, cur) && !satisfies(v, depVerCon(d.con)) {
						ok = false
						break
					}
				}
			}
			// Conflict constraints from already-assigned packages that target 'name'.
			for j := 0; j < i && ok; j++ {
				pj := names[j]
				for _, c := range verConflicts[pj][cur[pj]] {
					if c.name == name && conflictFires(c.con, v, cur) {
						ok = false
						break
					}
				}
			}
			// Dep constraints from 'name'@v that target already-assigned packages.
			if ok {
				for _, d := range verDeps[name][v] {
					if idx, found := nameIdx[d.name]; found && idx < i {
						if depActive(d.con, cur) && !satisfies(cur[d.name], depVerCon(d.con)) {
							ok = false
							break
						}
					}
				}
			}
			// Conflict constraints from 'name'@v that target already-assigned packages.
			if ok {
				for _, c := range verConflicts[name][v] {
					if idx, found := nameIdx[c.name]; found && idx < i {
						if conflictFires(c.con, cur[c.name], cur) {
							ok = false
							break
						}
					}
				}
			}
			if ok && search(i+1) {
				return true // Found the lexicographically-greatest valid assignment.
			}
		}
		cur[name] = ""
		return false
	}
	if !search(0) {
		return nil, fmt.Errorf("no version selection satisfies all constraints")
	}
	selected := cur

	// Pass 1.5: transitive extra resolution.
	// A spec's activated extras add deps to the chosen release. Each such extra
	// package is resolved to the HIGHEST version that (a) satisfies its accumulated
	// constraints, (b) does not conflict with the current selection, and (c) has
	// FEASIBLE own deps (some release of each dep can satisfy the constraint). The
	// chosen extra's OWN deps are then resolved by the same rules, recursively, so
	// extras carry a full transitive sub-closure rather than being flat leaves. A
	// candidate whose deps are infeasible, or that conflicts with the selection, is
	// skipped in favor of a lower release.
	extraCons := map[string][]string{}           // child pkg -> accumulated constraints
	extraParents := map[string]map[string]bool{} // child pkg -> set of parent pkg names
	extraSelected := map[string]string{}         // extra pkg -> chosen version
	allSel := map[string]string{}                // main selection + extras chosen so far
	for k, v := range selected {
		allSel[k] = v
	}
	var queue []string
	enqueue := func(child, parent, con string) {
		if extraParents[child] == nil {
			extraParents[child] = map[string]bool{}
		}
		extraParents[child][parent] = true
		if inPkg[child] {
			return // already resolved by the main solver: contributes an edge only
		}
		extraCons[child] = append(extraCons[child], con)
		queue = append(queue, child)
	}
	// feasibleDep reports whether depName can satisfy con: for a main-closure
	// package, its already-selected version must satisfy; otherwise some release
	// must exist that satisfies.
	feasibleDep := func(depName, con string) bool {
		if inPkg[depName] {
			return satisfies(selected[depName], con)
		}
		for _, v := range pkgVersions[depName] {
			if satisfies(v, con) {
				return true
			}
		}
		return false
	}
	// Seed from spec-level activated extras (deterministic spec order).
	seedNames := make([]string, 0, len(specNames))
	for s := range specNames {
		seedNames = append(seedNames, s)
	}
	sort.Strings(seedNames)
	for _, s := range seedNames {
		extrasInSpec, hasExtras := specPkgExtras[s]
		if !hasExtras {
			continue
		}
		for _, p := range specPkgs[s] {
			reqExtras, ok := extrasInSpec[p.name]
			if !ok || isVirtual(p.name) {
				continue
			}
			selVer := selected[p.name]
			if selVer == "" {
				continue
			}
			for _, extName := range reqExtras {
				for _, d := range verExtras[p.name][selVer][extName] {
					enqueue(d.name, p.name, d.con)
				}
			}
		}
	}
	// Resolve the extra sub-closure with a deterministic worklist.
	resolved := map[string]bool{}
	for len(queue) > 0 {
		name := queue[0]
		queue = queue[1:]
		if resolved[name] || inPkg[name] {
			continue
		}
		versions := make([]string, len(pkgVersions[name]))
		copy(versions, pkgVersions[name])
		sort.Slice(versions, func(i, j int) bool { return cmpVer(versions[i], versions[j]) > 0 })
		chosen := ""
		for _, v := range versions {
			ok := true
			for _, c := range extraCons[name] {
				if !satisfies(v, c) {
					ok = false
					break
				}
			}
			if ok {
				for _, cf := range verConflicts[name][v] {
					if sv, has := allSel[cf.name]; has && conflictFires(cf.con, sv, allSel) {
						ok = false
						break
					}
				}
			}
			if ok {
				for _, d := range verDeps[name][v] {
					if !feasibleDep(d.name, d.con) {
						ok = false
						break
					}
				}
			}
			if ok {
				chosen = v
				break
			}
		}
		if chosen == "" {
			return nil, fmt.Errorf("no valid version for extra package %s", name)
		}
		extraSelected[name] = chosen
		allSel[name] = chosen
		resolved[name] = true
		// Recurse into the chosen release's own deps.
		for _, d := range verDeps[name][chosen] {
			enqueue(d.name, name, d.con)
		}
	}

	// Pass 2: virtual dep resolution.
	// For each virtual dep referenced from a spec, find the best real provider.
	// "Best" = highest provided_version that satisfies the constraint AND has no
	// conflict with the current selection AND whose own deps are satisfied.
	type virtualResolution struct{ virtual, pkg, ver string }
	var virtualResolutions []virtualResolution
	virtualSeen := map[string]bool{}

	for s := range specNames {
		for _, p := range specPkgs[s] {
			if !isVirtual(p.name) {
				continue
			}
			if virtualSeen[p.name] {
				continue
			}
			virtualSeen[p.name] = true

			candidates := append([]provCand(nil), virtualProviders[p.name]...)
			// Sort by provided_version descending; prefer highest provided version.
			sort.Slice(candidates, func(i, j int) bool {
				return cmpVer(candidates[i].providedVer, candidates[j].providedVer) > 0
			})

			chosen := false
			for _, c := range candidates {
				if !satisfies(c.providedVer, p.con) {
					continue // provided version doesn't satisfy the constraint
				}
				// Check: does this release conflict with any selected real package?
				conflictHit := false
				for _, cf := range verConflicts[c.pkg][c.ver] {
					if inPkg[cf.name] && conflictFires(cf.con, selected[cf.name], selected) {
						conflictHit = true
						break
					}
				}
				if conflictHit {
					continue
				}
				// Check: are this release's deps satisfied by selected packages?
				depOK := true
				for _, d := range verDeps[c.pkg][c.ver] {
					if inPkg[d.name] && !satisfies(selected[d.name], d.con) {
						depOK = false
						break
					}
				}
				if !depOK {
					continue
				}
				virtualResolutions = append(virtualResolutions, virtualResolution{p.name, c.pkg, c.ver})
				chosen = true
				break
			}
			if !chosen {
				return nil, fmt.Errorf("no valid provider for virtual dep %s %s", p.name, p.con)
			}
		}
	}

	// providerOf maps virtual name → resolved pkg node ID
	providerOf := map[string]string{}
	for _, vr := range virtualResolutions {
		providerOf[vr.virtual] = "pkg:" + vr.pkg + "@" + vr.ver
	}

	pkgID := func(name string) string { return "pkg:" + name + "@" + selected[name] }
	tcID := func(name string) string { return "tc:" + name + "@" + tcVersion[name] }

	nodes := map[string]*node{}
	for s := range specNames {
		id := "spec:" + s
		nodes[id] = &node{ID: id, Type: "spec", Name: s, Version: ""}
	}
	for p := range inPkg {
		id := pkgID(p)
		nodes[id] = &node{ID: id, Type: "package", Name: p, Version: selected[p]}
	}
	for t := range inTc {
		id := tcID(t)
		nodes[id] = &node{ID: id, Type: "toolchain", Name: t, Version: tcVersion[t]}
	}
	// Add provider nodes for virtual deps (not in inPkg — added in pass 2)
	for _, vr := range virtualResolutions {
		provID := "pkg:" + vr.pkg + "@" + vr.ver
		if _, exists := nodes[provID]; !exists {
			nodes[provID] = &node{ID: provID, Type: "package", Name: vr.pkg, Version: vr.ver}
		}
	}
	// Add extra package nodes (pass 1.5 results — not in inPkg)
	for eName, eVer := range extraSelected {
		eid := "pkg:" + eName + "@" + eVer
		if _, exists := nodes[eid]; !exists {
			nodes[eid] = &node{ID: eid, Type: "package", Name: eName, Version: eVer}
		}
	}

	addEdge := func(from, to string) {
		n := nodes[from]
		for _, d := range n.Deps {
			if d == to {
				return
			}
		}
		n.Deps = append(n.Deps, to)
	}
	for s := range specNames {
		for _, p := range specPkgs[s] {
			if isVirtual(p.name) {
				// Edge from spec to the resolved provider
				if provID, ok := providerOf[p.name]; ok {
					addEdge("spec:"+s, provID)
				}
			} else {
				addEdge("spec:"+s, pkgID(p.name))
			}
		}
		for _, t := range specTcs[s] {
			addEdge("spec:"+s, tcID(t))
		}
		// Spec-to-spec ordering constraints: this spec must build after required specs.
		for _, req := range specRequires[s] {
			addEdge("spec:"+s, "spec:"+req)
		}
	}
	for p := range inPkg {
		for _, d := range verDeps[p][selected[p]] {
			if depActive(d.con, selected) {
				addEdge(pkgID(p), pkgID(d.name))
			}
		}
	}
	// Add edges from each parent to its extra dep node (pass 1.5). A parent may be
	// a main-closure package or another extra package; a child may be an extra
	// package or (if an extra dep points back into the main closure) a resolved
	// main package.
	nodeVer := func(name string) string {
		if inPkg[name] {
			return selected[name]
		}
		return extraSelected[name]
	}
	for child, parents := range extraParents {
		childID := "pkg:" + child + "@" + nodeVer(child)
		for parentName := range parents {
			addEdge("pkg:"+parentName+"@"+nodeVer(parentName), childID)
		}
	}
	// Add edges from provider nodes to their real-package deps
	for _, vr := range virtualResolutions {
		provID := "pkg:" + vr.pkg + "@" + vr.ver
		for _, d := range verDeps[vr.pkg][vr.ver] {
			if inPkg[d.name] {
				addEdge(provID, pkgID(d.name))
			}
		}
	}
	for t := range inTc {
		for _, r := range tcReqTc[t] {
			addEdge(tcID(t), tcID(r))
		}
		for _, r := range tcReqPkg[t] {
			addEdge(tcID(t), pkgID(r.name))
		}
	}
	for _, n := range nodes {
		sort.Strings(n.Deps)
	}

	// Drop any package no spec ends up needing. The closure search space (inPkg)
	// is a conservative union of dep names across every release of a package, so
	// that the search has a fixed variable set to assign before any version is
	// chosen. But once versions are actually selected, a package pulled into that
	// union only by a release that was NOT the one selected for its parent may
	// have no real path from any spec at all. Filter the final node set down to
	// what's reachable from the spec roots using only the edges that reflect the
	// ACTUAL selected versions (already built above), so a name that is only a
	// dependency of a non-chosen release of its parent never appears as a phantom
	// node in the output.
	reachable := map[string]bool{}
	var visitReach func(string)
	visitReach = func(id string) {
		if reachable[id] {
			return
		}
		reachable[id] = true
		if n, ok := nodes[id]; ok {
			for _, d := range n.Deps {
				visitReach(d)
			}
		}
	}
	for s := range specNames {
		visitReach("spec:" + s)
	}
	for id := range nodes {
		if !reachable[id] {
			delete(nodes, id)
		}
	}

	// Deterministic Kahn topological sort with lexicographic tie-break by id.
	indeg := map[string]int{}
	dependents := map[string][]string{}
	for id, n := range nodes {
		indeg[id] = len(n.Deps)
		for _, d := range n.Deps {
			dependents[d] = append(dependents[d], id)
		}
	}
	ready := []string{}
	for id := range nodes {
		if indeg[id] == 0 {
			ready = append(ready, id)
		}
	}
	sort.Strings(ready)
	insert := func(s []string, v string) []string {
		i := sort.SearchStrings(s, v)
		s = append(s, "")
		copy(s[i+1:], s[i:])
		s[i] = v
		return s
	}
	order := []*node{}
	for len(ready) > 0 {
		id := ready[0]
		ready = ready[1:]
		order = append(order, nodes[id])
		deps := append([]string(nil), dependents[id]...)
		sort.Strings(deps)
		for _, a := range deps {
			indeg[a]--
			if indeg[a] == 0 {
				ready = insert(ready, a)
			}
		}
	}
	if len(order) != len(nodes) {
		return nil, fmt.Errorf("dependency cycle detected")
	}
	return order, nil
}

type planNode struct {
	ID        string   `json:"id"`
	Type      string   `json:"type"`
	Name      string   `json:"name"`
	Version   string   `json:"version"`
	DependsOn []string `json:"depends_on"`
}

type planOut struct {
	BuildOrder []planNode `json:"build_order"`
	NodeCount  int        `json:"node_count"`
	EdgeCount  int        `json:"edge_count"`
}

func cmdPlan(dbPath, outPath string) error {
	order, err := resolve(dbPath)
	if err != nil {
		return err
	}
	out := &planOut{}
	edges := 0
	for _, n := range order {
		deps := n.Deps
		if deps == nil {
			deps = []string{}
		}
		edges += len(deps)
		out.BuildOrder = append(out.BuildOrder, planNode{
			ID: n.ID, Type: n.Type, Name: n.Name, Version: n.Version, DependsOn: deps,
		})
	}
	out.NodeCount = len(order)
	out.EdgeCount = edges
	data, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(outPath, append(data, '\n'), 0o644)
}

func cmdGraph(dbPath, outPath string) error {
	order, err := resolve(dbPath)
	if err != nil {
		return err
	}
	ids := make([]string, 0, len(order))
	typeOf := map[string]string{}
	type edge struct{ from, to string }
	var edges []edge
	for _, n := range order {
		ids = append(ids, n.ID)
		typeOf[n.ID] = n.Type
		for _, d := range n.Deps {
			edges = append(edges, edge{n.ID, d})
		}
	}
	sort.Strings(ids)
	sort.Slice(edges, func(i, j int) bool {
		if edges[i].from != edges[j].from {
			return edges[i].from < edges[j].from
		}
		return edges[i].to < edges[j].to
	})
	var b strings.Builder
	b.WriteString("digraph depmap {\n")
	for _, id := range ids {
		b.WriteString(fmt.Sprintf("  %q [type=%q];\n", id, typeOf[id]))
	}
	for _, e := range edges {
		b.WriteString(fmt.Sprintf("  %q -> %q;\n", e.from, e.to))
	}
	b.WriteString("}\n")
	return os.WriteFile(outPath, []byte(b.String()), 0o644)
}

func flagVal(args []string, name string) string {
	for i := 0; i < len(args); i++ {
		if args[i] == name && i+1 < len(args) {
			return args[i+1]
		}
		if strings.HasPrefix(args[i], name+"=") {
			return strings.TrimPrefix(args[i], name+"=")
		}
	}
	return ""
}

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: depmap <import|plan|graph> [flags]")
		os.Exit(2)
	}
	args := os.Args[2:]
	var err error
	switch os.Args[1] {
	case "import":
		err = cmdImport(flagVal(args, "--specs"), flagVal(args, "--locks"), flagVal(args, "--toolchains"), flagVal(args, "--db"))
	case "plan":
		err = cmdPlan(flagVal(args, "--db"), flagVal(args, "--out"))
	case "graph":
		err = cmdGraph(flagVal(args, "--db"), flagVal(args, "--out"))
	default:
		fmt.Fprintf(os.Stderr, "unknown command %q\n", os.Args[1])
		os.Exit(2)
	}
	if err != nil {
		fmt.Fprintln(os.Stderr, "error:", err)
		os.Exit(1)
	}
}
GOEOF

CGO_ENABLED=0 go build -o /usr/local/bin/depmap .

mkdir -p /app/out
depmap import --specs /app/data/specs --locks /app/data/locks/packages.lock.json --toolchains /app/data/toolchains.json --db /app/out/build.db
depmap plan --db /app/out/build.db --out /app/out/build-plan.json
depmap graph --db /app/out/build.db --out /app/out/depgraph.dot
