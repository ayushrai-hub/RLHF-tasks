package knobs

import (
	"os"
	"strconv"
)

type Knobs struct {
	FDStep           float64
	GradTol          float64
	PoolClearSecond  bool
	PassOrderDefault string
}

func ResolveKnobs(cfg map[string]any, pol map[string]string) Knobs {
	out := Knobs{
		FDStep:           1e-5,
		GradTol:          1e-4,
		PoolClearSecond:  true,
		PassOrderDefault: "first",
	}
	if v, ok := cfg["fd_step"].(float64); ok && v > 0 {
		out.FDStep = v
	}
	if v, ok := cfg["grad_tol"].(float64); ok && v > 0 {
		out.GradTol = v
	}
	if v, ok := pol["pass_order_default"]; ok && v != "" {
		out.PassOrderDefault = v
	}
	if v, ok := pol["pool_clear_on_second"]; ok {
		out.PoolClearSecond = v == "true"
	}
	_ = os.Getenv
	_ = strconv.ParseFloat
	return out
}
