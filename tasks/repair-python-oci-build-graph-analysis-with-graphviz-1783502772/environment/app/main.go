// Command depmap reconstructs container build/dependency order from OCI-style
// spec fixtures. It imports specs, a package lock, and toolchain metadata into
// a SQLite database, then resolves the build graph from that database.
//
// NOTE: this is an early prototype. `import` is wired up and trustworthy, but
// `plan` and `graph` only handle the simplest single-layer case: they look at
// the direct packages named on each spec, pick the first listed release, and
// ignore transitive deps, toolchains, per-version constraint solving,
// deterministic ordering, and the dependency edges in the graph. Those are all
// still missing.
package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
)

// ---------- fixture types ----------

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
	Version   string                 `json:"version"`
	Deps      []lockDep              `json:"deps"`
	Conflicts []lockDep              `json:"conflicts"`
	Provides  []provideEntry         `json:"provides"`
	Extras    map[string][]lockDep   `json:"extras"`
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

// ---------- sqlite helpers (drive the sqlite3 CLI) ----------

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

// ---------- import ----------

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

// ---------- plan / graph output types ----------

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

// naivePlan only looks at the direct packages named on each spec. It picks the
// first version listed for a package and ignores transitive deps, toolchains,
// per-version constraints and ordering. This is the prototype behaviour that
// needs fixing.
func naivePlan(dbPath string) (*planOut, error) {
	pkgRows, err := sqlQuery(dbPath, "SELECT name, version FROM packages;")
	if err != nil {
		return nil, err
	}
	firstVer := map[string]string{}
	for _, r := range pkgRows {
		if _, ok := firstVer[r["name"]]; !ok {
			firstVer[r["name"]] = r["version"]
		}
	}

	spkgRows, err := sqlQuery(dbPath, "SELECT spec, package FROM spec_packages;")
	if err != nil {
		return nil, err
	}

	seen := map[string]bool{}
	out := &planOut{}
	for _, r := range spkgRows { // map/query order, not deterministic by design
		name := r["package"]
		if seen[name] {
			continue
		}
		seen[name] = true
		v := firstVer[name]
		out.BuildOrder = append(out.BuildOrder, planNode{
			ID:        "pkg:" + name + "@" + v,
			Type:      "package",
			Name:      name,
			Version:   v,
			DependsOn: []string{},
		})
	}
	out.NodeCount = len(out.BuildOrder)
	out.EdgeCount = 0
	return out, nil
}

func cmdPlan(dbPath, outPath string) error {
	p, err := naivePlan(dbPath)
	if err != nil {
		return err
	}
	data, err := json.MarshalIndent(p, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(outPath, append(data, '\n'), 0o644)
}

func cmdGraph(dbPath, outPath string) error {
	p, err := naivePlan(dbPath)
	if err != nil {
		return err
	}
	var b strings.Builder
	b.WriteString("digraph depmap {\n")
	for _, n := range p.BuildOrder {
		b.WriteString(fmt.Sprintf("  %q [type=%q];\n", n.ID, n.Type))
	}
	// edges are not emitted yet
	b.WriteString("}\n")
	return os.WriteFile(outPath, []byte(b.String()), 0o644)
}

// ---------- CLI ----------

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
