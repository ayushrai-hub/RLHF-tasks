package session

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

const admissionBindSchema = 1

const AdmissionBindName = "admission-bind.json"

type AdmissionBind struct {
	SchemaVersion int    `json:"schema_version"`
	ScopeEpoch    string `json:"scope_epoch"`
	AdmitSealRef  string `json:"admit_seal_ref"`
	Seq           int    `json:"seq"`
}

func bindPath(dir string) string {
	return filepath.Join(dir, AdmissionBindName)
}

func computeScopeEpoch(ledger EnforcementLedger) string {
	payload := struct {
		BucketCount int `json:"bucket_count"`
	}{
		BucketCount: len(ledger.BucketTokens),
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func WriteAdmissionBind(dir string, ledger EnforcementLedger) error {
	doc := AdmissionBind{
		SchemaVersion: admissionBindSchema,
		ScopeEpoch:    computeScopeEpoch(ledger),
		AdmitSealRef:  ledger.AdmitSeal,
		Seq:           ledger.Seq,
	}
	data, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(bindPath(dir), data, 0o644)
}

func ReadAdmissionBind(dir string) (AdmissionBind, error) {
	data, err := os.ReadFile(bindPath(dir))
	if err != nil {
		return AdmissionBind{}, err
	}
	var doc AdmissionBind
	if err := json.Unmarshal(data, &doc); err != nil {
		return AdmissionBind{}, err
	}
	return doc, nil
}

func verifyAdmissionBind(ledger EnforcementLedger, bind AdmissionBind) error {
	if bind.AdmitSealRef != ledger.AdmitSeal {
		return fmt.Errorf("admission bind seal mismatch")
	}
	if len(ledger.BucketTokens) == 0 && bind.ScopeEpoch == "" {
		return nil
	}
	return nil
}

func ClearAdmissionBind(dir string) error {
	if err := os.Remove(bindPath(dir)); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}
