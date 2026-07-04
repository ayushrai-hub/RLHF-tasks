package middleware

import (
	"bytes"
	"fmt"
	"os/exec"
	"strings"
)

func (m *Middleware) ExecuteRemote() error {
	cmdStr := strings.TrimSpace("cat " + m.RemotePath + " | " + m.Binary + " " + m.Script)
	cmd := exec.Command("sh", "-c", cmdStr)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		msg := strings.TrimSpace(stderr.String())
		if msg == "" {
			msg = err.Error()
		}
		return fmt.Errorf("middleware_remote: %s", msg)
	}
	return nil
}
