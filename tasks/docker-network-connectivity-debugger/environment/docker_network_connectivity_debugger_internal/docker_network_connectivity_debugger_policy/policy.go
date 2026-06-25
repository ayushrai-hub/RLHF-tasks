package policy

// ResolveBools applies scenario defaults and policy_overrides for connectivity flags.
func ResolveBools(requireShared, blockEdge, requireTLS bool, overrides map[string]interface{}) (bool, bool, bool) {
	if overrides == nil {
		return requireShared, blockEdge, requireTLS
	}
	if v, ok := overrides["require_shared_network"]; ok {
		if b, ok := toBool(v); ok {
			requireShared = b
		}
	}
	if v, ok := overrides["block_edge_to_internal"]; ok {
		if b, ok := toBool(v); ok {
			blockEdge = b
		}
	}
	if v, ok := overrides["require_tls_on_internal"]; ok {
		if b, ok := toBool(v); ok {
			requireTLS = b
		}
	}
	return requireShared, blockEdge, requireTLS
}

func toBool(v interface{}) (bool, bool) {
	switch x := v.(type) {
	case bool:
		return x, true
	default:
		return false, false
	}
}
