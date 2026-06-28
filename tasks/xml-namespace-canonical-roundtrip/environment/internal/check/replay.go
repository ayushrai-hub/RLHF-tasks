package check

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"nsx/internal/model"
	"nsx/internal/run"
)

func Artifacts(out string) error {
	for _, name := range []string{run.CanonicalName, run.ScopeName, run.AuditName} {
		path := filepath.Join(out, name)
		if info, err := os.Stat(path); err != nil || info.IsDir() || info.Size() == 0 {
			return fmt.Errorf("missing or empty artifact %s", path)
		}
	}
	if err := checkAudit(run.AuditPath(out)); err != nil {
		return err
	}
	entries, err := os.ReadDir(out)
	if err != nil {
		return err
	}
	for _, entry := range entries {
		if strings.HasSuffix(entry.Name(), ".tmp") {
			return fmt.Errorf("temporary file left in output: %s", entry.Name())
		}
	}
	return nil
}

func ScopeDocument(doc *model.Document, artifact string) error {
	if doc == nil || doc.Root == nil {
		return fmt.Errorf("empty document")
	}
	raw, err := os.ReadFile(run.ScopePath(artifact))
	if err != nil {
		return err
	}
	var got model.ScopeFile
	if err := json.Unmarshal(raw, &got); err != nil {
		return err
	}
	if got.Version != "nsx-scope-v1" {
		return fmt.Errorf("scope version mismatch")
	}
	if got.Input != doc.Input {
		return fmt.Errorf("scope input path mismatch")
	}
	return nil
}

func InputMarker(artifact, input string) error {
	raw, err := os.ReadFile(run.InputMarkerPath(artifact))
	if err != nil {
		return fmt.Errorf("missing input marker: %w", err)
	}
	got := strings.TrimSpace(string(raw))
	if got != input {
		return fmt.Errorf("input marker mismatch")
	}
	return nil
}

func ExpectedNamespaceURIs(doc *model.Document) []string {
	uris := doc.UsedURIs()
	sort.Strings(uris)
	return uris
}

func checkAudit(path string) error {
	fh, err := os.Open(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	want := []string{"parse", "normalize", "serialize", "validate"}
	scanner := bufio.NewScanner(fh)
	idx := 0
	for scanner.Scan() {
		var line struct {
			Phase  string `json:"phase"`
			Status string `json:"status"`
		}
		if err := json.Unmarshal(scanner.Bytes(), &line); err != nil {
			return err
		}
		if idx >= len(want) || line.Phase != want[idx] {
			return fmt.Errorf("unexpected audit phase %q at row %d", line.Phase, idx)
		}
		if line.Status != "ok" {
			return fmt.Errorf("audit phase %s is not ok", line.Phase)
		}
		idx++
	}
	if err := scanner.Err(); err != nil {
		return err
	}
	if idx != len(want) {
		return fmt.Errorf("audit had %d phases, want %d", idx, len(want))
	}
	return nil
}
