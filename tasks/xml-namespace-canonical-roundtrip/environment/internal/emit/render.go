package emit

import (
	"fmt"
	"strings"

	"nsx/internal/model"
)

func Render(doc *model.Document) (string, error) {
	if doc == nil || doc.Root == nil {
		return "", fmt.Errorf("empty document")
	}
	table := NewPrefixTable(doc)
	var b strings.Builder
	renderNode(&b, doc.Root, table, true)
	b.WriteByte('\n')
	return b.String(), nil
}

func renderNode(b *strings.Builder, node *model.Node, table PrefixTable, root bool) {
	b.WriteByte('<')
	b.WriteString(table.QName(node.Name))
	if root {
		for i, uri := range table.URIs {
			b.WriteString(fmt.Sprintf(" xmlns:n%d=\"%s\"", i, EscapeAttr(uri)))
		}
	}
	for _, attr := range node.Attrs {
		b.WriteByte(' ')
		b.WriteString(table.QName(attr.Name))
		b.WriteString("=\"")
		b.WriteString(EscapeAttr(attr.Value))
		b.WriteByte('"')
	}
	if len(node.Children) == 0 && node.Text == "" {
		b.WriteString("/>")
		return
	}
	b.WriteByte('>')
	if node.Text != "" {
		b.WriteString(EscapeText(node.Text))
	}
	for _, child := range node.Children {
		renderNode(b, child, table, false)
	}
	b.WriteString("</")
	b.WriteString(table.QName(node.Name))
	b.WriteByte('>')
}
