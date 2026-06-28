package load

import (
	"encoding/xml"
	"fmt"
	"os"
	"strings"

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
			frames[len(frames)-1].ApplyAll(decls)
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
	key := strings.ToLower(name.Local)
	counts[key]++
	return fmt.Sprintf("%s/%d", stack[len(stack)-1].Path, counts[key])
}
