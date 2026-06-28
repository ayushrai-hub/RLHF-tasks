package model

type Document struct {
	Input       string
	Root        *Node
	DeclOrder   []Binding
	NodeCounter int
}

func (d *Document) AddBinding(b Binding) {
	for _, seen := range d.DeclOrder {
		if seen.Prefix == b.Prefix && seen.URI == b.URI {
			return
		}
	}
	d.DeclOrder = append(d.DeclOrder, b)
}

func (d *Document) UsedURIs() []string {
	seen := map[string]bool{}
	var out []string
	if d.Root == nil {
		return out
	}
	d.Root.Walk(func(n *Node) {
		if n.Name.URI != "" && !seen[n.Name.URI] {
			seen[n.Name.URI] = true
			out = append(out, n.Name.URI)
		}
		for _, attr := range n.Attrs {
			if attr.Name.URI != "" && !seen[attr.Name.URI] {
				seen[attr.Name.URI] = true
				out = append(out, attr.Name.URI)
			}
		}
	})
	return out
}
