package policy

func Resolve(
	featureScale string,
	calibrationGate bool,
	overrides map[string]interface{},
) (string, bool) {
	if overrides == nil {
		return featureScale, calibrationGate
	}
	if v, ok := overrides["feature_scale_mode"]; ok {
		if s, ok := v.(string); ok && (s == "global" || s == "per_device") {
			featureScale = s
		}
	}
	if v, ok := overrides["calibration_gate"]; ok {
		if b, ok := v.(bool); ok {
			calibrationGate = b
		}
	}
	return featureScale, calibrationGate
}
