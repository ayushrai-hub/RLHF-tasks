package pk_c

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"lab/pk_b"
	"os"
	"path/filepath"
	"sort"
	"time"
)

// ReconcileC emits gzip bytes and ledger rows with size-bound row fingerprints, topographically sorted.
func ReconcileC(reachable pk_b.ReachSet, blobs BlobPack, out PackEmitter, ledger *LedgerEmitter) error {
	outEdges := make(map[string][]string)
	inDegree := make(map[string]int)
	for _, n := range reachable.Nodes {
		if _, ok := inDegree[n.NodeID]; !ok {
			inDegree[n.NodeID] = 0
		}
		for _, dep := range n.Deps {
			outEdges[dep] = append(outEdges[dep], n.NodeID)
			inDegree[n.NodeID]++
			if _, ok := inDegree[dep]; !ok {
				inDegree[dep] = 0
			}
		}
	}
	
	var available []string
	for n, deg := range inDegree {
		if deg == 0 {
			available = append(available, n)
		}
	}
	
	var members []string
	for len(available) > 0 {
		sort.Strings(available)
		curr := available[0]
		available = available[1:]
		members = append(members, curr)
		for _, child := range outEdges[curr] {
			inDegree[child]--
			if inDegree[child] == 0 {
				available = append(available, child)
			}
		}
	}
	
	for _, bid := range members {
		if _, ok := blobs.Sizes[bid]; !ok {
			panic("unknown blob size for " + bid)
		}
	}

	rows := make([]LedgerRow, len(members))
	body := &bytes.Buffer{}
	for i, bid := range members {
		blen := blobs.Sizes[bid]
		body.WriteString(bid)
		body.WriteByte('|')
		body.WriteString(itoa(blen))
		body.WriteByte('\n')
		rows[i] = LedgerRow{BlobID: bid, RowFP: rowFP(bid, blen), OrdIdx: i}
	}
	
	sum := sha256.Sum256(body.Bytes())
	digest := hex.EncodeToString(sum[:])

	if err := os.MkdirAll(filepath.Dir(out.Path), 0o755); err != nil {
		return err
	}
	
	var gz bytes.Buffer
	w, err := gzip.NewWriterLevel(&gz, gzip.DefaultCompression)
	if err != nil {
		return err
	}
	w.Header = gzip.Header{ModTime: time.Unix(0, 0)}
	if _, err := w.Write(body.Bytes()); err != nil {
		return err
	}
	if err := w.Close(); err != nil {
		return err
	}
	
	// Atomic bundle write
	tmpOut := out.Path + ".tmp"
	if err := os.WriteFile(tmpOut, gz.Bytes(), 0o644); err != nil {
		return err
	}
	os.Rename(tmpOut, out.Path)

	doc := map[string]any{
		"pack_id":       ledger.PackID,
		"bundle_digest": digest,
		"rows":          rows,
		"audit_trail":   getAuditTrail(),
	}
	raw, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(ledger.Path), 0o755); err != nil {
		return err
	}
	tmpLedger := ledger.Path + ".tmp"
	if err := os.WriteFile(tmpLedger, raw, 0o644); err != nil {
		return err
	}
	return os.Rename(tmpLedger, ledger.Path)
}

func rowFP(blobID string, byteLen int) string {
	sum := sha256.Sum256([]byte(blobID + "|" + itoa(byteLen)))
	return hex.EncodeToString(sum[:])
}

func getAuditTrail() []int {
	raw, err := os.ReadFile("/app/output/inc_store/seed.json")
	if err != nil {
		return nil
	}
	var doc struct {
		History []int `json:"history"`
	}
	json.Unmarshal(raw, &doc)
	return doc.History
}

func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	var buf [20]byte
	i := len(buf)
	for n > 0 {
		i--
		buf[i] = byte('0' + n%10)
		n /= 10
	}
	if neg {
		i--
		buf[i] = '-'
	}
	return string(buf[i:])
}
