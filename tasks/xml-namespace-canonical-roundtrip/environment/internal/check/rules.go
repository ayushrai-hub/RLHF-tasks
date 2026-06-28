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
		seen := map[string]bool{}
		for _, attr := range n.Attrs {
			key := attr.Name.Key() + "\x00" + attr.Value
			if seen[key] {
				first = fmt.Errorf("duplicate attribute expanded name on %s: %s", n.Path, attr.Name.String())
				return
			}
			seen[key] = true
		}
	})
	return first
}
