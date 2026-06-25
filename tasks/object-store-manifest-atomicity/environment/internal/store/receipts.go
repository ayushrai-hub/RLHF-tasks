package store

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type Receipt struct {
	SchemaVersion int          `json:"schema_version"`
	BatchID       string       `json:"batch_id"`
	Phase         string       `json:"phase"`
	Epoch         int          `json:"epoch"`
	Objects       []ObjectSpec `json:"objects"`
}

type ReceiptFile struct {
	Path    string
	Receipt Receipt
}

func ReadReceipt(path string) (Receipt, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return Receipt{}, err
	}
	var r Receipt
	if err := json.Unmarshal(raw, &r); err != nil {
		return Receipt{}, err
	}
	return r, nil
}

func ReadReceipts(layout Layout) ([]ReceiptFile, error) {
	entries, err := os.ReadDir(layout.ReceiptsDir())
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	out := make([]ReceiptFile, 0, len(entries))
	for _, entry := range entries {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".receipt.json") {
			continue
		}
		path := filepath.Join(layout.ReceiptsDir(), entry.Name())
		receipt, err := ReadReceipt(path)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		out = append(out, ReceiptFile{Path: path, Receipt: receipt})
	}
	sort.Slice(out, func(i, j int) bool {
		return out[i].Receipt.BatchID < out[j].Receipt.BatchID
	})
	return out, nil
}

func ReceiptNameBatch(path string) string {
	name := filepath.Base(path)
	return strings.TrimSuffix(name, ".receipt.json")
}
