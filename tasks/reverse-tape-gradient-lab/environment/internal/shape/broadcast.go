
package shape

func ResolvePass(graph map[string]any, policy map[string]string, envOrder string) string {
  if envOrder != "" {
    return envOrder
  }
  if po, ok := graph["pass_order"].(string); ok && po != "" {
    return po
  }
  if d, ok := policy["pass_order_default"]; ok && d != "" {
    return d
  }
  return "first"
}
