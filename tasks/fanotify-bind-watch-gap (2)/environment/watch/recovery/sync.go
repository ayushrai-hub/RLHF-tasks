package recovery

import (
	"os"
	"path/filepath"

	"arrivaudit/mount/fanout"
)

// RecycleMarkers realigns work-view state after a host-side observer pause.
func RecycleMarkers(ctx *fanout.Context) error {
	if ctx == nil {
		return os.ErrInvalid
	}
	hostLog := filepath.Join(ctx.HostView, "active.log")
	workLog := filepath.Join(ctx.WorkView, "active.log")
	body, err := os.ReadFile(hostLog)
	if err != nil {
		return err
	}
	if err := os.WriteFile(workLog, body, 0o644); err != nil {
		return err
	}
	return nil
}
