package main

import (
	"encoding/json"
	"os"
	"path/filepath"

	"fedenv/internal/ward"
)

func main() {
	e := ward.NewEngine(ward.DefaultConfig())
	e.InstallKey("k-alpha", 1, []byte{1, 2, 3, 4})
	e.ReloadMap(map[string]string{"ext-probe": "principal-probe"})
	c := ward.Claim{
		Kid: "k-alpha", Gen: 1, Realm: "svc://payments.local", ExtID: "ext-probe",
		AnchorMs: 105_000, NotBefore: 100_000, NotAfter: 110_000,
	}
	c.Sig = ward.Sign([]byte{1, 2, 3, 4}, c)
	out := e.Admit(c)
	ready := out.Code == "ADMIT"
	_ = os.MkdirAll("/app/output/stage", 0o755)
	payload := map[string]any{
		"ready":     ready,
		"code":      out.Code,
		"principal": out.Principal,
	}
	b, _ := json.MarshalIndent(payload, "", "  ")
	_ = os.WriteFile(filepath.Join("/app/output/stage", "probe.json"), b, 0o644)
	if ready {
		os.Exit(0)
	}
	os.Exit(1)
}
