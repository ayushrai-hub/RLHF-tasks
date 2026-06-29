package model

type ScopeNode struct {
	Path       string      `json:"path"`
	Name       Name        `json:"name"`
	Declared   []Binding   `json:"declared"`
	Attributes []ScopeAttr `json:"attributes"`
}

type ScopeAttr struct {
	URI   string `json:"uri"`
	Local string `json:"local"`
	Value string `json:"value"`
}

type ScopeFile struct {
	Version       string      `json:"version"`
	Input         string      `json:"input"`
	NamespaceURIs []string    `json:"namespace_uris"`
	Nodes         []ScopeNode `json:"nodes"`
}
