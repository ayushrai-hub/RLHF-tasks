package main

import (
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const maxGzipBytes = 4800

var packs = []string{"sc_w1", "sc_c2", "sc_h3", "sc_j4"}

var heavyByPack = map[string]string{
	"sc_c2": "k9",
	"sc_h3": "z8",
}

func envRoot() string {
	if v := os.Getenv("Q7_ENV_ROOT"); v != "" {
		return v
	}
	return "/app/environment"
}

func drvBin() string {
	if v := os.Getenv("Q7_DRV_BIN"); v != "" {
		return v
	}
	return "/app/environment/tools/drv_q7/drv_q7"
}

func rowFP(blobID string, byteLen int) string {
	sum := sha256.Sum256([]byte(fmt.Sprintf("%s|%d", blobID, byteLen)))
	return hex.EncodeToString(sum[:])
}

func expectedDigest(rows []map[string]any, sizes map[string]int) string {
	lines := make([]string, 0, len(rows))
	for _, row := range rows {
		bid := row["blob_id"].(string)
		lines = append(lines, fmt.Sprintf("%s|%d", bid, sizes[bid]))
	}
	sum := sha256.Sum256([]byte(strings.Join(lines, "\n")))
	return hex.EncodeToString(sum[:])
}

func loadBlobSizes(packID string) (map[string]int, error) {
	raw, err := os.ReadFile(filepath.Join(envRoot(), "scenarios", packID+".toml"))
	if err != nil {
		return nil, err
	}
	blobFile := ""
	for _, line := range strings.Split(string(raw), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, "blob_file") {
			blobFile = strings.Trim(strings.TrimPrefix(line, "blob_file"), " =\"")
			break
		}
	}
	docRaw, err := os.ReadFile(filepath.Join(envRoot(), blobFile))
	if err != nil {
		return nil, err
	}
	var doc struct {
		Sizes map[string]int `json:"sizes"`
	}
	if err := json.Unmarshal(docRaw, &doc); err != nil {
		return nil, err
	}
	return doc.Sizes, nil
}

func validateLedger(ledgerPath string, sizes map[string]int) error {
	raw, err := os.ReadFile(ledgerPath)
	if err != nil {
		return err
	}
	var doc struct {
		Rows          []map[string]any `json:"rows"`
		BundleDigest  string           `json:"bundle_digest"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		return err
	}
	if len(doc.Rows) == 0 {
		return fmt.Errorf("empty ledger rows")
	}
	for _, row := range doc.Rows {
		bid := row["blob_id"].(string)
		fp := row["row_fp"].(string)
		if fp != rowFP(bid, sizes[bid]) {
			return fmt.Errorf("row_fp mismatch for %s", bid)
		}
	}
	expect := expectedDigest(doc.Rows, sizes)
	if doc.BundleDigest != expect {
		return fmt.Errorf("bundle_digest mismatch")
	}
	return nil
}

func validateReachability(packID, ledgerPath string) error {
	raw, err := os.ReadFile(ledgerPath)
	if err != nil {
		return err
	}
	var doc struct {
		Rows []struct {
			BlobID string `json:"blob_id"`
		} `json:"rows"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		return err
	}
	ids := map[string]struct{}{}
	for _, row := range doc.Rows {
		ids[row.BlobID] = struct{}{}
	}
	if packID == "sc_w1" {
		if _, ok := ids["k2"]; !ok {
			return fmt.Errorf("sc_w1 missing k2")
		}
		if _, ok := ids["k9"]; ok {
			return fmt.Errorf("sc_w1 must not include k9")
		}
	}
	if heavy, ok := heavyByPack[packID]; ok {
		if _, present := ids[heavy]; !present {
			return fmt.Errorf("%s missing heavy blob %s", packID, heavy)
		}
	}
	return nil
}

func runPack(packID, scratch string) error {
	bundle := filepath.Join(scratch, packID+"_bundle.cpio.gz")
	ledger := filepath.Join(scratch, packID+"_ledger.json")
	if err := os.MkdirAll(scratch, 0o755); err != nil {
		return err
	}
	cmd := exec.Command(drvBin(), "--pack", packID, "--bundle-out", bundle, "--ledger-out", ledger)
	cmd.Env = append(os.Environ(), "Q7_ENV_ROOT="+envRoot())
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("%w: %s", err, string(out))
	}
	info, err := os.Stat(bundle)
	if err != nil {
		return err
	}
	if info.Size() > maxGzipBytes {
		return fmt.Errorf("%s gzip length %d exceeds cap", packID, info.Size())
	}
	sizes, err := loadBlobSizes(packID)
	if err != nil {
		return err
	}
	if err := validateLedger(ledger, sizes); err != nil {
		return err
	}
	if err := validateReachability(packID, ledger); err != nil {
		return err
	}
	return validateBundleFormat(bundle, ledger, sizes)
}

func validateBundleFormat(bundlePath, ledgerPath string, sizes map[string]int) error {
	f, err := os.Open(bundlePath)
	if err != nil {
		return err
	}
	defer f.Close()

	gr, err := gzip.NewReader(f)
	if err != nil {
		return err
	}
	defer gr.Close()

	raw, err := io.ReadAll(gr)
	if err != nil {
		return err
	}

	lines := strings.Split(strings.TrimSpace(string(raw)), "\n")
	if len(lines) == 1 && lines[0] == "" {
		lines = nil
	}

	ledgerRaw, err := os.ReadFile(ledgerPath)
	if err != nil {
		return err
	}
	var doc struct {
		Rows []map[string]any `json:"rows"`
	}
	if err := json.Unmarshal(ledgerRaw, &doc); err != nil {
		return err
	}

	if len(lines) != len(doc.Rows) {
		return fmt.Errorf("bundle line count %d does not match ledger row count %d", len(lines), len(doc.Rows))
	}

	for i, row := range doc.Rows {
		bid := row["blob_id"].(string)
		expectedLine := fmt.Sprintf("%s|%d", bid, sizes[bid])
		if lines[i] != expectedLine {
			return fmt.Errorf("bundle line %d mismatch: got %q, want %q", i, lines[i], expectedLine)
		}
	}
	return nil
}

func gridAll(bundleOut, ledgerOut string) error {
	scratch := "/app/output/scratch"
	for _, packID := range packs {
		if err := runPack(packID, scratch); err != nil {
			return fmt.Errorf("%s: %w", packID, err)
		}
	}
	termBundle := filepath.Join(scratch, "sc_j4_bundle.cpio.gz")
	termLedger := filepath.Join(scratch, "sc_j4_ledger.json")
	bundleRaw, err := os.ReadFile(termBundle)
	if err != nil {
		return err
	}
	ledgerRaw, err := os.ReadFile(termLedger)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(bundleOut), 0o755); err != nil {
		return err
	}
	if err := os.WriteFile(bundleOut, bundleRaw, 0o644); err != nil {
		return err
	}
	return os.WriteFile(ledgerOut, ledgerRaw, 0o644)
}
