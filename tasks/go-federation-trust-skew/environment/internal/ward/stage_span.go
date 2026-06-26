package ward

import (
	"fedenv/chorus/chrono"
)

func checkWindow(cfg Config, c Claim) bool {
	anchor := chrono.WindowAnchor(c.AnchorMs, c.NotBefore, c.NotAfter)
	return chrono.WindowOpen(anchor, c.NotBefore, c.NotAfter, cfg.Slack)
}
