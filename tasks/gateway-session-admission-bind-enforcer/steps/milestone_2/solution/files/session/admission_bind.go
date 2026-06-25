package session

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
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

func scopeEpochFromLedger(ledger EnforcementLedger) string {
	ids := make([]string, 0, len(ledger.BucketTokens))
	for id := range ledger.BucketTokens {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	tokens := make(map[string]int, len(ids))
	for _, id := range ids {
		tokens[id] = ledger.BucketTokens[id]
	}
	payload := struct {
		AdmitSeal    string         `json:"admit_seal"`
		BucketTokens map[string]int `json:"bucket_tokens"`
		ConfigGen    int            `json:"config_gen"`
		ScopeGen     int            `json:"scope_gen"`
		Seq          int            `json:"seq"`
	}{
		AdmitSeal:    ledger.AdmitSeal,
		BucketTokens: tokens,
		ConfigGen:    ledger.ConfigGen,
		ScopeGen:     ledger.ScopeGen,
		Seq:          ledger.Seq,
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func WriteAdmissionBind(dir string, ledger EnforcementLedger) error {
	doc := AdmissionBind{
		SchemaVersion: admissionBindSchema,
		ScopeEpoch:    scopeEpochFromLedger(ledger),
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
	if bind.Seq != ledger.Seq {
		return fmt.Errorf("admission bind seq mismatch")
	}
	if bind.ScopeEpoch != scopeEpochFromLedger(ledger) {
		return fmt.Errorf("admission bind scope epoch mismatch")
	}
	return nil
}

func ClearAdmissionBind(dir string) error {
	if err := os.Remove(bindPath(dir)); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}
