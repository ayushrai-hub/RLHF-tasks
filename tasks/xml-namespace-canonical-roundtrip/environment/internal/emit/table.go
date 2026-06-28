package emit

import (
	"fmt"

	"nsx/internal/model"
)

type PrefixTable struct {
	ByURI map[string]string
	URIs  []string
}

func NewPrefixTable(doc *model.Document) PrefixTable {
	seen := map[string]bool{}
	var ordered []string
	for _, decl := range doc.DeclOrder {
		if decl.URI == "" || seen[decl.URI] {
			continue
		}
		seen[decl.URI] = true
		ordered = append(ordered, decl.URI)
	}
	for _, uri := range doc.UsedURIs() {
		if uri == "" || seen[uri] {
			continue
		}
		seen[uri] = true
		ordered = append(ordered, uri)
	}
	byURI := map[string]string{}
	for i, uri := range ordered {
		byURI[uri] = fmt.Sprintf("n%d", i)
	}
	return PrefixTable{ByURI: byURI, URIs: ordered}
}

func (p PrefixTable) QName(name model.Name) string {
	if name.URI == "" {
		return name.Local
	}
	return p.ByURI[name.URI] + ":" + name.Local
}
