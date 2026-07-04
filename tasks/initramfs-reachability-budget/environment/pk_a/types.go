package pk_a

type GraphNode struct {
	NodeID string
	Deps   []string
}

type IngestSink struct {
	Rows     map[string]GraphNode
	Registry map[string]GraphNode
}
