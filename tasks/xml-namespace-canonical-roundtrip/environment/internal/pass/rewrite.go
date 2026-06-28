package pass

import "nsx/internal/model"

func Apply(doc *model.Document) {
	if doc == nil || doc.Root == nil {
		return
	}
	doc.Root.Walk(func(n *model.Node) {
		n.Text = CleanText(n.Text)
		SortAttributes(n.Attrs)
	})
}
