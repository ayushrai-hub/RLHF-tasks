package session

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"gateway-session/rate"
)

const checkpointSchemaVersion = 1

const genesisCheckpointDigest = "0000000000000000000000000000000000000000000000000000000000000000"

type Checkpoint struct {
	SchemaVersion        int    `json:"schema_version"`
	Seq                  int    `json:"seq"`
	RunID                string `json:"run_id"`
	ConfigGen            int    `json:"config_gen"`
	ScopeGen             int    `json:"scope_gen"`
	BucketFingerprint    string `json:"bucket_fingerprint"`
	PrevCheckpointDigest string `json:"prev_checkpoint_digest"`
	CheckpointDigest     string `json:"checkpoint_digest"`
}

type checkpointDigestPayload struct {
	BucketFingerprint string `json:"bucket_fingerprint"`
	ConfigGen         int    `json:"config_gen"`
	RunID             string `json:"run_id"`
	SchemaVersion     int    `json:"schema_version"`
	ScopeGen          int    `json:"scope_gen"`
	Seq               int    `json:"seq"`
}

func checkpointBodyDigest(cp Checkpoint) string {
	payload := checkpointDigestPayload{
		BucketFingerprint: cp.BucketFingerprint,
		ConfigGen:         cp.ConfigGen,
		RunID:             cp.RunID,
		SchemaVersion:     cp.SchemaVersion,
		ScopeGen:          cp.ScopeGen,
		Seq:               cp.Seq,
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func finalizeCheckpoint(cp Checkpoint, prevDigest string) Checkpoint {
	cp.PrevCheckpointDigest = prevDigest
	cp.CheckpointDigest = checkpointBodyDigest(cp)
	return cp
}

func bucketFingerprint(buckets map[string]rate.Bucket) string {
	ids := make([]string, 0, len(buckets))
	for id := range buckets {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	view := make(map[string]int, len(ids))
	for _, id := range ids {
		view[id] = buckets[id].Tokens
	}
	raw, _ := json.Marshal(view)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func loadCheckpointFile(path string) (Checkpoint, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Checkpoint{}, err
	}
	var cp Checkpoint
	if err := json.Unmarshal(data, &cp); err != nil {
		return Checkpoint{}, err
	}
	return cp, nil
}

func loadCheckpointChain(dir string) ([]Checkpoint, error) {
	var chain []Checkpoint

	archiveDir := filepath.Join(dir, "checkpoints")
	entries, err := os.ReadDir(archiveDir)
	if err != nil && !os.IsNotExist(err) {
		return nil, err
	}
	if err == nil {
		for _, entry := range entries {
			if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".json") {
				continue
			}
			cp, err := loadCheckpointFile(filepath.Join(archiveDir, entry.Name()))
			if err != nil {
				return nil, err
			}
			chain = append(chain, cp)
		}
	}

	headPath := filepath.Join(dir, "checkpoint.json")
	if _, err := os.Stat(headPath); err == nil {
		cp, err := loadCheckpointFile(headPath)
		if err != nil {
			return nil, err
		}
		chain = append(chain, cp)
	} else if !os.IsNotExist(err) {
		return nil, err
	}

	sort.Slice(chain, func(i, j int) bool {
		return chain[i].Seq < chain[j].Seq
	})
	return chain, nil
}

func verifyCheckpointChain(dir string) error {
	chain, err := loadCheckpointChain(dir)
	if err != nil {
		return err
	}
	prevDigest := genesisCheckpointDigest
	for _, cp := range chain {
		if cp.CheckpointDigest != checkpointBodyDigest(cp) {
			return fmt.Errorf("checkpoint digest mismatch at seq %d", cp.Seq)
		}
		if cp.PrevCheckpointDigest != prevDigest {
			return fmt.Errorf("checkpoint chain broken at seq %d", cp.Seq)
		}
		prevDigest = cp.CheckpointDigest
	}
	return nil
}

func archiveHeadCheckpoint(dir string) (string, error) {
	headPath := filepath.Join(dir, "checkpoint.json")
	data, err := os.ReadFile(headPath)
	if os.IsNotExist(err) {
		return genesisCheckpointDigest, nil
	}
	if err != nil {
		return "", err
	}
	var cp Checkpoint
	if err := json.Unmarshal(data, &cp); err != nil {
		return "", err
	}
	archiveDir := filepath.Join(dir, "checkpoints")
	if err := os.MkdirAll(archiveDir, 0o755); err != nil {
		return "", err
	}
	archivePath := filepath.Join(archiveDir, strconv.Itoa(cp.Seq)+".json")
	if err := os.WriteFile(archivePath, data, 0o644); err != nil {
		return "", err
	}
	if err := os.Remove(headPath); err != nil {
		return "", err
	}
	return cp.CheckpointDigest, nil
}

func ClearCheckpointChain(dir string) error {
	headPath := filepath.Join(dir, "checkpoint.json")
	if err := os.Remove(headPath); err != nil && !os.IsNotExist(err) {
		return err
	}
	archiveDir := filepath.Join(dir, "checkpoints")
	if err := os.RemoveAll(archiveDir); err != nil {
		return err
	}
	return nil
}

func writeCheckpoint(dir string, cp Checkpoint) error {
	data, err := json.MarshalIndent(cp, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "checkpoint.json"), data, 0o644)
}
