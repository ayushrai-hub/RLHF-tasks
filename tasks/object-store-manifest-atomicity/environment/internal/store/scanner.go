package store

import (
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type TreeObject struct {
	BatchID      string
	LogicalKey   string
	RelativePath string
	SidecarPath  string
	Size         int64
	SHA256       string
}

func ScanObjectTree(layout Layout) ([]TreeObject, error) {
	objectsDir := layout.ObjectsDir()
	rows := []TreeObject{}
	err := filepath.WalkDir(objectsDir, func(path string, entry os.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if entry.IsDir() || strings.HasSuffix(entry.Name(), ".sha256") || !strings.HasSuffix(entry.Name(), ".dat") {
			return nil
		}
		relFromObjects, err := filepath.Rel(objectsDir, path)
		if err != nil {
			return err
		}
		parts := strings.Split(filepath.ToSlash(relFromObjects), "/")
		if len(parts) < 2 {
			return nil
		}
		batchID := parts[0]
		logical := strings.TrimSuffix(strings.Join(parts[1:], "/"), ".dat")
		relToRoot, err := filepath.Rel(layout.Root, path)
		if err != nil {
			return err
		}
		size, digest, err := ReadObjectDigest(path)
		if err != nil {
			return err
		}
		rows = append(rows, TreeObject{
			BatchID:      batchID,
			LogicalKey:   logical,
			RelativePath: filepath.ToSlash(relToRoot),
			SidecarPath:  path + ".sha256",
			Size:         size,
			SHA256:       digest,
		})
		return nil
	})
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].BatchID != rows[j].BatchID {
			return rows[i].BatchID < rows[j].BatchID
		}
		return rows[i].LogicalKey < rows[j].LogicalKey
	})
	return rows, nil
}
