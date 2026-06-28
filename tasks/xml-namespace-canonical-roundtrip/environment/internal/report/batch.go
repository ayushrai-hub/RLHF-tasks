package report

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"nsx/internal/run"
)

type BatchRow struct {
	Input           string `json:"input"`
	ArtifactDir     string `json:"artifact_dir"`
	CanonicalSHA256 string `json:"canonical_sha256"`
}

func WriteBatchLedger(out string, rows []BatchRow) error {
	sort.Slice(rows, func(i, j int) bool {
		return rows[i].Input < rows[j].Input
	})
	path := run.BatchLedgerPath(out)
	fh, err := os.Create(path)
	if err != nil {
		return err
	}
	defer fh.Close()
	enc := json.NewEncoder(fh)
	for _, row := range rows {
		if err := enc.Encode(row); err != nil {
			return err
		}
	}
	return nil
}

func CanonicalSHA256(artifactDir string) (string, error) {
	raw, err := os.ReadFile(run.ScopePath(artifactDir))
	if err != nil {
		return "", err
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:]), nil
}

func ReadBatchList(path string) ([]string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []string
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		out = append(out, line)
	}
	return out, nil
}

func PrepareBatchOutput(out string, memberDirs []string) error {
	if err := os.MkdirAll(out, 0o755); err != nil {
		return err
	}
	if err := os.Remove(run.BatchLedgerPath(out)); err != nil && !os.IsNotExist(err) {
		return err
	}
	for _, member := range memberDirs {
		if err := os.MkdirAll(member, 0o755); err != nil {
			return err
		}
	}
	return nil
}

func MemberDir(out, input string) string {
	base := filepath.Base(input)
	ext := filepath.Ext(base)
	if ext != "" {
		base = strings.TrimSuffix(base, ext)
	}
	return filepath.Join(out, base)
}
