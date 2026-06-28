package report

import (
	"encoding/json"
	"os"
	"time"

	"nsx/internal/run"
)

type AuditLine struct {
	Phase  string `json:"phase"`
	Status string `json:"status"`
	Input  string `json:"input"`
	Output string `json:"output"`
	UnixMs int64  `json:"unix_ms"`
}

type Audit struct {
	Input string
	Out   string
	Lines []AuditLine
}

func NewAudit(input, out string) *Audit {
	return &Audit{Input: input, Out: out}
}

func (a *Audit) Add(phase, status string) {
	a.Lines = append(a.Lines, AuditLine{
		Phase:  phase,
		Status: status,
		Input:  a.Input,
		Output: a.Out,
		UnixMs: time.Now().UnixMilli(),
	})
}

func WriteAudit(out string, audit *Audit) error {
	path := run.AuditPath(out)
	fh, err := os.Create(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	enc := json.NewEncoder(fh)
	for _, line := range audit.Lines {
		if err := enc.Encode(line); err != nil {
			return err
		}
	}
	return nil
}
