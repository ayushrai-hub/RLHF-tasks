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
	next := Frame{Bindings: map[string]string{}}
	for k, v := range f.Bindings {
		next.Bindings[k] = v
	}
	for _, decl := range decls {
		if decl.Prefix == "" && decl.URI == "" {
			continue
		}
		next.Bindings[decl.Prefix] = decl.URI
	}
	return next
}

func (f Frame) ApplyAll(decls []Binding) {
	for _, decl := range decls {
		if decl.Prefix == "" && decl.URI == "" {
			continue
		}
		if f.Bindings == nil {
			f.Bindings = map[string]string{}
		}
		f.Bindings[decl.Prefix] = decl.URI
	}
}

func (f Frame) Lookup(prefix string) string {
	return f.Bindings[prefix]
}
