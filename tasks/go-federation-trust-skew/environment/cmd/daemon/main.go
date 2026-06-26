package main

import (
	"fmt"
	"time"

	"fedenv/internal/ward"
)

func main() {
	e := ward.NewEngine(ward.DefaultConfig())
	e.InstallKey("k-alpha", 1, []byte{1, 2, 3, 4})
	e.ReloadMap(map[string]string{"ext-daemon": "principal-daemon"})
	c := ward.Claim{
		Kid: "k-alpha", Gen: 1, Realm: "svc://payments.local", ExtID: "ext-daemon",
		AnchorMs: 105_000, NotBefore: 100_000, NotAfter: 110_000,
	}
	c.Sig = ward.Sign([]byte{1, 2, 3, 4}, c)
	out := e.Admit(c)
	fmt.Printf("daemon admit code=%s principal=%s at %s\n", out.Code, out.Principal, time.Now().UTC().Format(time.RFC3339))
}
