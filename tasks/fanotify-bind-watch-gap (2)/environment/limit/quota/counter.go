package quota

import (
	"fmt"
	"os"
	"path/filepath"
)

type Counter struct {
	root string
}

func NewCounter(workspace string) *Counter {
	return &Counter{root: filepath.Join(workspace, "archive")}
}

func (c *Counter) Bump(hostView, workView string, next int) error {
	payload := []byte(fmt.Sprintf("%d\n", next))
	for _, view := range []string{hostView, workView} {
		if err := os.MkdirAll(view, 0o755); err != nil {
			return err
		}
		if err := os.WriteFile(filepath.Join(view, "wave_gen"), payload, 0o644); err != nil {
			return err
		}
	}
	return nil
}
