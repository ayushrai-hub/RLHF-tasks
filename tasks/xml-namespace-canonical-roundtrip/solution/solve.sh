#!/usr/bin/env bash
set -euo pipefail

cd /app/environment

cat > internal/model/frame.go <<'GO'
package model

type Binding struct {
	Prefix string `json:"prefix"`
	URI    string `json:"uri"`
}

type Frame struct {
	Bindings map[string]string
}

func RootFrame() Frame {
	return Frame{Bindings: map[string]string{
		"xml": "http://www.w3.org/XML/1998/namespace",
	}}
}

func (f Frame) Fork(decls []Binding) Frame {
	next := Frame{Bindings: cloneBindings(f.Bindings)}
	next.ApplyAll(decls)
	return next
}

func (f Frame) ApplyAll(decls []Binding) {
	for _, decl := range decls {
		f.Apply(decl)
	}
}

func (f Frame) Apply(decl Binding) {
	if f.Bindings == nil {
		f.Bindings = map[string]string{}
	}
	f.Bindings[decl.Prefix] = decl.URI
}

func cloneBindings(in map[string]string) map[string]string {
	out := make(map[string]string, len(in))
	for prefix, uri := range in {
		out[prefix] = uri
	}
	return out
}

func (f Frame) Lookup(prefix string) string {
	return f.Bindings[prefix]
}
GO

cat > internal/load/attrs.go <<'GO'
package load

import (
	"encoding/xml"

	"nsx/internal/model"
)

func Declarations(attrs []xml.Attr) []model.Binding {
	var decls []model.Binding
	for _, attr := range attrs {
		binding, ok := DeclarationBinding(attr)
		if !ok {
			continue
		}
		decls = append(decls, binding)
	}
	return decls
}

func DeclarationBinding(attr xml.Attr) (model.Binding, bool) {
	if attr.Name.Space == "" && attr.Name.Local == "xmlns" {
		return model.Binding{Prefix: "", URI: attr.Value}, true
	}
	if attr.Name.Space == "xmlns" {
		return model.Binding{Prefix: attr.Name.Local, URI: attr.Value}, true
	}
	return model.Binding{}, false
}

func IsNamespaceDeclaration(attr xml.Attr) bool {
	_, ok := DeclarationBinding(attr)
	return ok
}

func RegularAttributes(attrs []xml.Attr, frame model.Frame) []model.Attribute {
	out := make([]model.Attribute, 0, len(attrs))
	for _, attr := range attrs {
		if IsNamespaceDeclaration(attr) {
			continue
		}
		out = append(out, model.Attribute{
			Name:  ExpandedAttributeName(attr, frame),
			Value: attr.Value,
		})
	}
	return out
}

func ExpandedAttributeName(attr xml.Attr, _ model.Frame) model.Name {
	return model.Name{URI: attr.Name.Space, Local: attr.Name.Local}
}
GO

cat > internal/load/read.go <<'GO'
package load

import (
	"encoding/xml"
	"fmt"
	"os"

	"nsx/internal/model"
)

func ReadFile(path string) (*model.Document, error) {
	fh, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer fh.Close()

	decoder := xml.NewDecoder(fh)
	decoder.Strict = true
	doc := &model.Document{Input: path}
	frames := []model.Frame{model.RootFrame()}
	var stack []*model.Node
	var childCounters []map[string]int

	for {
		tok, err := decoder.Token()
		if err != nil {
			if err.Error() == "EOF" {
				break
			}
			return nil, err
		}
		switch item := tok.(type) {
		case xml.StartElement:
			decls := Declarations(item.Attr)
			for _, decl := range decls {
				doc.AddBinding(decl)
			}
			frame := frames[len(frames)-1].Fork(decls)
			name := ElementName(item.Name, frame)
			attrs := RegularAttributes(item.Attr, frame)
			path := nextPath(stack, childCounters, name)
			node := &model.Node{Name: name, Attrs: attrs, Path: path, Declared: decls}
			if len(stack) == 0 {
				doc.Root = node
			} else {
				parent := stack[len(stack)-1]
				parent.Children = append(parent.Children, node)
			}
			stack = append(stack, node)
			frames = append(frames, frame)
			childCounters = append(childCounters, map[string]int{})
		case xml.EndElement:
			if len(stack) == 0 {
				return nil, fmt.Errorf("unexpected close tag %s", item.Name.Local)
			}
			stack = stack[:len(stack)-1]
			frames = frames[:len(frames)-1]
			childCounters = childCounters[:len(childCounters)-1]
		case xml.CharData:
			if len(stack) > 0 {
				stack[len(stack)-1].Text += string([]byte(item))
			}
		}
	}
	if doc.Root == nil {
		return nil, fmt.Errorf("no document element found")
	}
	if len(stack) != 0 {
		return nil, fmt.Errorf("unclosed element %s", stack[len(stack)-1].Name.Local)
	}
	return doc, nil
}

func nextPath(stack []*model.Node, counters []map[string]int, name model.Name) string {
	if len(stack) == 0 {
		return "/1"
	}
	counts := counters[len(counters)-1]
	key := name.Key()
	counts[key]++
	return fmt.Sprintf("%s/%d", stack[len(stack)-1].Path, counts[key])
}
GO

cat > internal/pass/text.go <<'GO'
package pass

import "strings"

func CleanText(s string) string {
	fields := strings.Fields(s)
	if len(fields) == 0 {
		return ""
	}
	return strings.Join(fields, " ")
}
GO

cat > internal/pass/order.go <<'GO'
package pass

import (
	"sort"

	"nsx/internal/model"
)

func SortAttributes(attrs []model.Attribute) {
	sort.SliceStable(attrs, func(i, j int) bool {
		a, b := attrs[i], attrs[j]
		if a.Name.URI != b.Name.URI {
			return a.Name.URI < b.Name.URI
		}
		if a.Name.Local != b.Name.Local {
			return a.Name.Local < b.Name.Local
		}
		return a.Value < b.Value
	})
}
GO

cat > internal/emit/table.go <<'GO'
package emit

import (
	"fmt"
	"sort"

	"nsx/internal/model"
)

type PrefixTable struct {
	ByURI map[string]string
	URIs  []string
}

func NewPrefixTable(doc *model.Document) PrefixTable {
	ordered := CanonicalURIs(doc)
	byURI := map[string]string{}
	for i, uri := range ordered {
		byURI[uri] = prefixForIndex(i)
	}
	return PrefixTable{ByURI: byURI, URIs: ordered}
}

func CanonicalURIs(doc *model.Document) []string {
	if doc == nil {
		return nil
	}
	return sortedUniqueNonEmpty(doc.UsedURIs())
}

func sortedUniqueNonEmpty(values []string) []string {
	seen := map[string]bool{}
	for _, value := range values {
		if value != "" {
			seen[value] = true
		}
	}
	ordered := make([]string, 0, len(seen))
	for value := range seen {
		ordered = append(ordered, value)
	}
	sort.Strings(ordered)
	return ordered
}

func prefixForIndex(i int) string {
	return fmt.Sprintf("n%d", i)
}

func (p PrefixTable) QName(name model.Name) string {
	if name.URI == "" {
		return name.Local
	}
	return p.ByURI[name.URI] + ":" + name.Local
}
GO

cat > internal/check/rules.go <<'GO'
package check

import (
	"fmt"

	"nsx/internal/model"
)

func Document(doc *model.Document) error {
	if doc == nil || doc.Root == nil {
		return fmt.Errorf("empty document")
	}
	var first error
	doc.Root.Walk(func(n *model.Node) {
		if first != nil {
			return
		}
		first = checkAttributeUniqueness(n)
	})
	return first
}

func checkAttributeUniqueness(entry *model.Node) error {
	seen := map[string]bool{}
	for _, attr := range entry.Attrs {
		key := attributeIdentity(attr)
		if seen[key] {
			return duplicateAttributeError(entry, attr)
		}
		seen[key] = true
	}
	return nil
}

func attributeIdentity(attr model.Attribute) string {
	return attr.Name.Key()
}

func duplicateAttributeError(entry *model.Node, attr model.Attribute) error {
	return fmt.Errorf("duplicate attribute expanded name on %s: %s", entry.Path, attr.Name.String())
}
GO

cat > internal/check/replay.go <<'GO'
package check

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"nsx/internal/model"
	"nsx/internal/run"
)

func Artifacts(out string) error {
	for _, name := range []string{run.CanonicalName, run.ScopeName, run.AuditName, run.InputMarkerName} {
		path := filepath.Join(out, name)
		if info, err := os.Stat(path); err != nil || info.IsDir() || info.Size() == 0 {
			return fmt.Errorf("missing or empty artifact %s", path)
		}
	}
	if err := checkAudit(run.AuditPath(out)); err != nil {
		return err
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if strings.HasSuffix(entry.Name(), ".tmp") {
			return fmt.Errorf("temporary file left in output: %s", entry.Name())
		}
	}
	return nil
}

func ScopeDocument(doc *model.Document, artifact string) error {
	if doc == nil || doc.Root == nil {
		return fmt.Errorf("empty document")
	}
	raw, err := os.ReadFile(run.ScopePath(artifact))
	if err != nil {
		return err
	}
	var got model.ScopeFile
	if err := json.Unmarshal(raw, &got); err != nil {
		return err
	}
	if got.Version != "nsx-scope-v1" {
		return fmt.Errorf("scope version mismatch")
	}
	if got.Input != doc.Input {
		return fmt.Errorf("scope input path mismatch")
	}
	wantURIs := ExpectedNamespaceURIs(doc)
	if !equalStrings(got.NamespaceURIs, wantURIs) {
		return fmt.Errorf("scope namespace_uris mismatch")
	}
	wantNodes := collectScopeNodes(doc)
	if len(got.Nodes) != len(wantNodes) {
		return fmt.Errorf("scope node count mismatch")
	}
	for i := range wantNodes {
		if got.Nodes[i].Path != wantNodes[i].Path {
			return fmt.Errorf("scope node path mismatch")
		}
		if got.Nodes[i].Name != wantNodes[i].Name {
			return fmt.Errorf("scope node name mismatch")
		}
		if !equalBindings(got.Nodes[i].Declared, wantNodes[i].Declared) {
			return fmt.Errorf("scope node declared mismatch")
		}
		if !equalScopeAttrs(got.Nodes[i].Attributes, wantNodes[i].Attributes) {
			return fmt.Errorf("scope node attributes mismatch")
		}
	}
	return nil
}

func InputMarker(artifact, input string) error {
	raw, err := os.ReadFile(run.InputMarkerPath(artifact))
	if err != nil {
		return fmt.Errorf("missing input marker: %w", err)
	}
	got := strings.TrimSpace(string(raw))
	if got != input {
		return fmt.Errorf("input marker mismatch")
	}
	return nil
}

func ExpectedNamespaceURIs(doc *model.Document) []string {
	uris := doc.UsedURIs()
	sort.Strings(uris)
	return uris
}

func collectScopeNodes(doc *model.Document) []model.ScopeNode {
	var nodes []model.ScopeNode
	doc.Root.Walk(func(n *model.Node) {
		entry := model.ScopeNode{Path: n.Path, Name: n.Name, Declared: n.Declared}
		for _, attr := range n.Attrs {
			entry.Attributes = append(entry.Attributes, model.ScopeAttr{
				URI: attr.Name.URI, Local: attr.Name.Local, Value: attr.Value,
			})
		}
		nodes = append(nodes, entry)
	})
	return nodes
}

func equalStrings(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func equalBindings(a, b []model.Binding) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func equalScopeAttrs(a, b []model.ScopeAttr) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func checkAudit(path string) error {
	fh, err := os.Open(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	want := []string{"parse", "normalize", "serialize", "validate"}
	scanner := bufio.NewScanner(fh)
	idx := 0
	for scanner.Scan() {
		var line struct {
			Phase  string `json:"phase"`
			Status string `json:"status"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &line); err != nil {
			return err
		}
		if idx >= len(want) || line.Phase != want[idx] {
			return fmt.Errorf("unexpected audit phase %q at row %d", line.Phase, idx)
		}
		if line.Status != "ok" {
			return fmt.Errorf("audit phase %s is not ok", line.Phase)
		}
		idx++
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	if idx != len(want) {
		return fmt.Errorf("audit had %d phases, want %d", idx, len(want))
	}
	return nil
}
GO

cat > internal/report/scope.go <<'GO'
package report

import (
	"encoding/json"
	"os"
	"sort"

	"nsx/internal/model"
	"nsx/internal/run"
)

func WriteScope(out string, doc *model.Document) error {
	file := model.ScopeFile{Version: "nsx-scope-v1", Input: doc.Input}
	uris := doc.UsedURIs()
	sort.Strings(uris)
	file.NamespaceURIs = uris
	doc.Root.Walk(func(n *model.Node) {
		entry := model.ScopeNode{Path: n.Path, Name: n.Name, Declared: n.Declared}
		for _, attr := range n.Attrs {
			entry.Attributes = append(entry.Attributes, model.ScopeAttr{URI: attr.Name.URI, Local: attr.Name.Local, Value: attr.Value})
		}
		file.Nodes = append(file.Nodes, entry)
	})
	payload, err := json.MarshalIndent(file, "", "  ")
	if err != nil {
		return err
	}
	payload = append(payload, '\n')
	return os.WriteFile(run.ScopePath(out), payload, 0o644)
}
GO

cat > internal/report/files.go <<'GO'
package report

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"

	"nsx/internal/run"
)

func PrepareOutput(out string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		name := entry.Name()
		if name == run.CanonicalName || name == run.ScopeName || name == run.AuditName || name == run.InputMarkerName || strings.HasSuffix(name, ".tmp") {
			if err := os.RemoveAll(filepath.Join(out, name)); err != nil {
				return err
			}
		}
	}
	return nil
}

func WriteCanonical(out, canonical string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	path := run.CanonicalPath(out)
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, []byte(canonical), fs.FileMode(0o644)); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func WriteInputMarker(out, input string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	return os.WriteFile(run.InputMarkerPath(out), []byte(input+"\n"), 0o644)
}
GO

cat > internal/report/batch.go <<'GO'
package report

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"nsx/internal/run"
)

type BatchRow struct {
	Input           string `json:"input"`
	ArtifactDir     string `json:"artifact_dir"`
	CanonicalSHA256 string `json:"canonical_sha256"`
}

func WriteBatchLedger(out string, rows []BatchRow) error {
	sort.Slice(rows, func(i, j int) bool {
		return rows[i].Input < rows[j].Input
	})
	path := run.BatchLedgerPath(out)
	fh, err := os.Create(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	enc := json.NewEncoder(fh)
	for _, row := range rows {
		if err := enc.Encode(row); err != nil {
			return err
		}
	}
	return nil
}

func CanonicalSHA256(artifactDir string) (string, error) {
	raw, err := os.ReadFile(run.CanonicalPath(artifactDir))
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func ReadBatchList(path string) ([]string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		out = append(out, line)
	}
	return out, nil
}

func PrepareBatchOutput(out string, memberDirs []string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	want := map[string]bool{}
	for _, member := range memberDirs {
		want[member] = true
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		member := filepath.Join(out, entry.Name())
		if !want[member] {
			if err := os.RemoveAll(member); err != nil {
				return err
			}
		}
	}
	if err := os.Remove(run.BatchLedgerPath(out)); err != nil && !os.IsNotExist(err) {
		return err
	}
	for _, member := range memberDirs {
		if err := os.MkdirAll(member, 0o755); err != nil {
			return err
		}
	}
	return nil
}

func MemberDir(out, input string) string {
	base := filepath.Base(input)
	ext := filepath.Ext(base)
	if ext != "" {
		base = strings.TrimSuffix(base, ext)
	}
	return filepath.Join(out, base)
}
GO

gofmt -w internal/model/frame.go internal/load/attrs.go internal/load/read.go internal/pass/text.go internal/pass/order.go internal/emit/table.go internal/check/rules.go internal/check/replay.go internal/report/scope.go internal/report/files.go internal/report/batch.go
go test ./...
make install
