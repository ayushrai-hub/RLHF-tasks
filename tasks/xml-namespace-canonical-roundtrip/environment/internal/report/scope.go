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
	seen := map[string]bool{}
	var uris []string
	for _, decl := range doc.DeclOrder {
		if decl.URI == "" || seen[decl.URI] {
			continue
		}
		seen[decl.URI] = true
		uris = append(uris, decl.URI)
	}
	sort.Strings(uris)
	file.NamespaceURIs = uris
	var inherited []model.Binding
	doc.Root.Walk(func(n *model.Node) {
		declared := append([]model.Binding{}, inherited...)
		declared = append(declared, n.Declared...)
		inherited = append(inherited, n.Declared...)
		entry := model.ScopeNode{Path: n.Path, Name: n.Name, Declared: declared}
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
