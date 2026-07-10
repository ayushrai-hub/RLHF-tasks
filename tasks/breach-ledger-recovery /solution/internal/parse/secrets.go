package parse

import (
	"bytes"
	"compress/gzip"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"io"
	"os"
	"path/filepath"

	"breach-ledger/internal/model"
	"breach-ledger/internal/normalize"
)

type secretManifest struct {
	XORKeyHex      string `json:"xor_key_hex"`
	ExpectedSHA256 string `json:"expected_sha256"`
	Fragments      []struct {
		Path string `json:"path"`
	} `json:"fragments"`
}

func unitJ(dir string, ev *model.Evidence, issues *[]model.Issue) {
	data, err := os.ReadFile(filepath.Join(dir, "manifest.json"))
	if err != nil {
		model.AddIssue(issues, "missing_required_evidence", "secret manifest missing")
		return
	}
	var manifest secretManifest
	if json.Unmarshal(data, &manifest) != nil {
		model.AddIssue(issues, "secret_fragment_conflict", "secret manifest malformed")
		return
	}
	keyBytes, err := hex.DecodeString(manifest.XORKeyHex)
	if err != nil || len(keyBytes) != 1 {
		model.AddIssue(issues, "secret_fragment_conflict", "bad xor key")
		return
	}
	root := filepath.Dir(dir)
	var payload []byte
	for _, fragment := range manifest.Fragments {
		if !normalize.NP2(fragment.Path) {
			model.AddIssue(issues, "path_traversal", "unsafe secret fragment path")
			continue
		}
		raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(fragment.Path)))
		if err != nil {
			model.AddIssue(issues, "secret_fragment_conflict", "secret fragment missing")
			continue
		}
		encoded, err := base64.StdEncoding.DecodeString(string(bytes.TrimSpace(raw)))
		if err != nil {
			model.AddIssue(issues, "secret_fragment_conflict", "secret fragment base64")
			continue
		}
		for i := range encoded {
			encoded[i] ^= keyBytes[0]
		}
		gz, err := gzip.NewReader(bytes.NewReader(encoded))
		if err != nil {
			model.AddIssue(issues, "secret_fragment_conflict", "secret fragment gzip")
			continue
		}
		part, err := io.ReadAll(gz)
		gz.Close()
		if err != nil {
			model.AddIssue(issues, "secret_fragment_conflict", "secret fragment read")
			continue
		}
		payload = append(payload, part...)
		ev.Summary["secret_fragments"]++
	}
	sum := sha256.Sum256(payload)
	ev.SecretDigest = hex.EncodeToString(sum[:])
	if ev.SecretDigest != manifest.ExpectedSHA256 {
		model.AddIssue(issues, "secret_fragment_conflict", "secret digest mismatch")
		return
	}
	for _, line := range bytes.Split(payload, []byte{'\n'}) {
		text := normalize.NT1(string(line))
		if text != "" {
			addString(&ev.StolenSecrets, text)
		}
	}
	addString(&ev.IOCs, "secret-sha256:"+ev.SecretDigest)
}
