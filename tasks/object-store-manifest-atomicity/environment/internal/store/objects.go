package store

import (
	"fmt"
	"os"

	"terminal.local/objectmanifest/internal/hashutil"
)

type ObjectSpec struct {
	LogicalKey   string `json:"logical_key"`
	RelativePath string `json:"relative_path"`
	Size         int64  `json:"size"`
	SHA256       string `json:"sha256"`
}

func ReadObjectDigest(path string) (int64, string, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return 0, "", err
	}
	return int64(len(data)), hashutil.SHA256Hex(data), nil
}

func ValidateObjectBytes(path string, wantSize int64, wantDigest string) error {
	gotSize, gotDigest, err := ReadObjectDigest(path)
	if err != nil {
		return err
	}
	if gotSize != wantSize {
		return fmt.Errorf("size mismatch: got %d want %d", gotSize, wantSize)
	}
	if gotDigest != wantDigest {
		return fmt.Errorf("sha256 mismatch: got %s want %s", gotDigest, wantDigest)
	}
	return nil
}
