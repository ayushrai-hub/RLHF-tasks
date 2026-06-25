package store

import (
	"path/filepath"
)

type Layout struct {
	Root string
}

func NewLayout(root string) Layout {
	return Layout{Root: filepath.Clean(root)}
}

func (l Layout) ObjectsDir() string {
	return filepath.Join(l.Root, "objects")
}

func (l Layout) ReceiptsDir() string {
	return filepath.Join(l.Root, "receipts")
}

func (l Layout) ObjectPath(rel string) string {
	return filepath.Join(l.Root, filepath.FromSlash(rel))
}

func (l Layout) SidecarPath(rel string) string {
	return l.ObjectPath(rel) + ".sha256"
}

func (l Layout) ReceiptPath(batchID string) string {
	return filepath.Join(l.ReceiptsDir(), batchID+".receipt.json")
}
