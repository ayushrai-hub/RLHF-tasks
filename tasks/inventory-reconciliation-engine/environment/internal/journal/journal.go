package journal

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

type BatchRecord struct {
	Name         string `json:"name"`
	File         string `json:"file"`
	EventCount   int    `json:"event_count"`
	DurableBytes int    `json:"durable_bytes"`
}

type Manifest struct {
	Batches []BatchRecord `json:"batches"`
}

func StateRoot(root string) string {
	return filepath.Join(root, "state", "journal")
}

func ManifestPath(root string) string {
	return filepath.Join(StateRoot(root), "manifest.json")
}

func BatchPath(root, name string) string {
	return filepath.Join(StateRoot(root), "batches", name+".jsonl")
}

func LoadManifest(root string) (*Manifest, error) {
	path := ManifestPath(root)
	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return &Manifest{Batches: []BatchRecord{}}, nil
		}
		return nil, err
	}
	var m Manifest
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, err
	}
	return &m, nil
}

func SaveManifest(root string, m *Manifest) error {
	if err := os.MkdirAll(filepath.Join(StateRoot(root), "batches"), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(ManifestPath(root), data, 0o644)
}

func ImportBatch(root, name, eventsPath string) (bool, error) {
	m, err := LoadManifest(root)
	if err != nil {
		return false, err
	}
	for _, b := range m.Batches {
		if b.Name == name {
			return false, nil
		}
	}
	src, err := os.ReadFile(eventsPath)
	if err != nil {
		return false, err
	}
	dst := BatchPath(root, name)
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return false, err
	}
	if err := os.WriteFile(dst, src, 0o644); err != nil {
		return false, err
	}
	lines := splitNonBlank(string(src))
	rec := BatchRecord{
		Name:         name,
		File:         filepath.Base(dst),
		EventCount:   len(lines),
		DurableBytes: durableLength(string(src)),
	}
	m.Batches = append(m.Batches, rec)
	if err := SaveManifest(root, m); err != nil {
		return false, err
	}
	return true, nil
}

func durableLength(src string) int {
	return len(src)
}

func splitNonBlank(src string) []string {
	var out []string
	for _, line := range strings.Split(src, "\n") {
		if strings.TrimSpace(line) != "" {
			out = append(out, line)
		}
	}
	return out
}

func ReadAllEvents(root string) ([][]byte, int, int, error) {
	m, err := LoadManifest(root)
	if err != nil {
		return nil, 0, 0, err
	}
	var all [][]byte
	lineCount := 0
	malformed := 0
	for _, batch := range m.Batches {
		path := filepath.Join(StateRoot(root), "batches", batch.File)
		data, err := os.ReadFile(path)
		if err != nil {
			return nil, 0, 0, err
		}
		content := string(data)
		if batch.DurableBytes > 0 && batch.DurableBytes <= len(content) {
			content = content[:batch.DurableBytes]
		}
		for _, line := range strings.Split(content, "\n") {
			if strings.TrimSpace(line) == "" {
				continue
			}
			lineCount++
			var obj map[string]any
			if json.Unmarshal([]byte(line), &obj) != nil {
				malformed++
				continue
			}
			all = append(all, []byte(line))
		}
	}
	return all, lineCount, malformed, nil
}

func TruncateTail(path string, keepBytes int) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	if keepBytes >= len(data) {
		return fmt.Errorf("nothing to truncate")
	}
	return os.WriteFile(path, data[:keepBytes], 0o644)
}
