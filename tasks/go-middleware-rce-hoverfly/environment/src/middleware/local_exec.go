package middleware

import (
	"bytes"
	"fmt"
	"os/exec"
	"strings"
)

func (m *Middleware) ExecuteLocal(payload []byte) error {
	cmdStr := strings.TrimSpace(m.Binary + " " + m.Script)
	cmd := exec.Command("sh", "-c", cmdStr)
	cmd.Stdin = bytes.NewReader(payload)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		msg := strings.TrimSpace(stderr.String())
		if msg == "" {
			msg = err.Error()
		}
		return fmt.Errorf("middleware_local: %s", msg)
	}
	return nil
}
