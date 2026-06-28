package model

type Attribute struct {
	Name  Name   `json:"name"`
	Value string `json:"value"`
}

type Node struct {
	Name       Name        `json:"name"`
	Attrs      []Attribute `json:"attributes"`
	Children   []*Node     `json:"children"`
	Text       string      `json:"text"`
	Path       string      `json:"path"`
	Declared   []Binding   `json:"declared"`
	ChildIndex int         `json:"-"`
}

func (n *Node) Walk(fn func(*Node)) {
	if n == nil {
		return
	}
	fn(n)
	for _, child := range n.Children {
		child.Walk(fn)
	}
}
