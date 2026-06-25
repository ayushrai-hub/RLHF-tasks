package store

import (
	"fmt"
	"os"
	"strings"
)

func ReadSidecarDigest(path string) (string, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	fields := strings.Fields(string(raw))
	if len(fields) == 0 {
		return "", fmt.Errorf("empty checksum sidecar")
	}
	return strings.ToLower(fields[0]), nil
}

func ValidateSidecarDigest(sidecarPath string, want string) error {
	got, err := ReadSidecarDigest(sidecarPath)
	if err != nil {
		return err
	}
	if got != strings.ToLower(want) {
		return fmt.Errorf("sidecar digest mismatch: got %s want %s", got, want)
	}
	return nil
}
