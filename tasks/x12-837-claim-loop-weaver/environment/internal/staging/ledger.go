package staging

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type WeaveLedger struct {
	Version             int    `json:"version"`
	ManifestFingerprint string `json:"manifest_fingerprint"`
	ErrorsDigest        string `json:"errors_digest"`
	ExportEpoch         int    `json:"export_epoch"`
}

func ErrorsDigest(errors []string) string {
	lines := append([]string(nil), errors...)
	sort.Strings(lines)
	payload := strings.Join(lines, "\n")
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:])
}

func ReadLedger(path string) (WeaveLedger, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return WeaveLedger{}, err
	}
	var ledger WeaveLedger
	if err := json.Unmarshal(data, &ledger); err != nil {
		return WeaveLedger{}, err
	}
	return ledger, nil
}

func WriteLedger(path string, ledger WeaveLedger) error {
	if ledger.Version == 0 {
		ledger.Version = 1
	}
	data, err := json.MarshalIndent(ledger, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func BuildLedger(snap WeaveSnapshot, ledgerPath string) WeaveLedger {
	digest := ErrorsDigest(snap.Errors)
	epoch := 1
	if prev, err := ReadLedger(ledgerPath); err == nil && prev.ExportEpoch > 0 {
		if prev.ManifestFingerprint == snap.ManifestFingerprint && prev.ErrorsDigest == digest {
			epoch = prev.ExportEpoch
		} else {
			epoch = prev.ExportEpoch + 1
		}
	}
	return WeaveLedger{
		Version:             1,
		ManifestFingerprint: snap.ManifestFingerprint,
		ErrorsDigest:        digest,
		ExportEpoch:         epoch,
	}
}
