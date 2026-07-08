
package compile

func TopoNodes(graph map[string]any) []map[string]any {
  nodes, _ := graph["nodes"].([]any)
  out := make([]map[string]any, 0, len(nodes))
  for _, raw := range nodes {
    if m, ok := raw.(map[string]any); ok {
      out = append(out, m)
    }
  }
  return out
}
