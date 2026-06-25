package session

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
)

const enforcementLedgerSchema = 1

const EnforcementLedgerName = "enforcement-ledger.json"

type EnforcementLedger struct {
	SchemaVersion      int            `json:"schema_version"`
	RunID              string         `json:"run_id"`
	BucketTokens       map[string]int `json:"bucket_tokens"`
	ConfigGen          int            `json:"config_gen"`
	ScopeGen           int            `json:"scope_gen"`
	RouteCounter       int            `json:"route_counter"`
	Seq                int            `json:"seq"`
	DigestPendingCount int            `json:"digest_pending_count"`
	AdmitSeal          string         `json:"admit_seal"`
}

func ledgerPath(dir string) string {
	return filepath.Join(dir, EnforcementLedgerName)
}

func ComputeAdmitSeal(
	runID string,
	bucketTokens map[string]int,
	configGen int,
	scopeGen int,
	routeCounter int,
	seq int,
	digestPendingCount int,
) string {
	ids := make([]string, 0, len(bucketTokens))
	for id := range bucketTokens {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	tokens := make(map[string]int, len(ids))
	for _, id := range ids {
		tokens[id] = bucketTokens[id]
	}
	payload := struct {
		BucketTokens       map[string]int `json:"bucket_tokens"`
		ConfigGen          int            `json:"config_gen"`
		DigestPendingCount int            `json:"digest_pending_count"`
		RouteCounter       int            `json:"route_counter"`
		RunID              string         `json:"run_id"`
		ScopeGen           int            `json:"scope_gen"`
		Seq                int            `json:"seq"`
	}{
		BucketTokens:       tokens,
		ConfigGen:          configGen,
		DigestPendingCount: digestPendingCount,
		RouteCounter:       routeCounter,
		RunID:              runID,
		ScopeGen:           scopeGen,
		Seq:                seq,
	}
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func WriteEnforcementLedger(dir string, ledger EnforcementLedger) error {
	ledger.SchemaVersion = enforcementLedgerSchema
	data, err := json.MarshalIndent(ledger, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(ledgerPath(dir), data, 0o644)
}

func ReadEnforcementLedger(dir string) (EnforcementLedger, error) {
	data, err := os.ReadFile(ledgerPath(dir))
	if err != nil {
		return EnforcementLedger{}, err
	}
	var ledger EnforcementLedger
	if err := json.Unmarshal(data, &ledger); err != nil {
		return EnforcementLedger{}, err
	}
	return ledger, nil
}
