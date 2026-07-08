package journal

import (
	"bufio"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
)

type RefreshEvent struct {
	Step          int    `json:"step"`
	Tick          int    `json:"tick"`
	Revision      int    `json:"revision"`
	ProofRevision int    `json:"proof_revision"`
	Accepted      bool   `json:"accepted"`
	Reason        string `json:"reason"`
}

func Path(dir string) string {
	return filepath.Join(dir, "refresh_journal.jsonl")
}

func Append(dir string, event RefreshEvent) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	f, err := os.OpenFile(Path(dir), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		return err
	}
	defer f.Close()
	payload, err := json.Marshal(event)
	if err != nil {
		return err
	}
	_, err = f.Write(append(payload, '\n'))
	return err
}

func Load(dir string) ([]RefreshEvent, error) {
	path := Path(dir)
	payload, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var events []RefreshEvent
	scanner := bufio.NewScanner(strings.NewReader(string(payload)))
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var event RefreshEvent
		if err := json.Unmarshal([]byte(line), &event); err != nil {
			return nil, err
		}
		events = append(events, event)
	}
	return events, scanner.Err()
}
