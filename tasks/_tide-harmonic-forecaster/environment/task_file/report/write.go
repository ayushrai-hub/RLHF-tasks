package report

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type Writer interface {
	Write(path string, doc Document)
}

type JSONWriter struct{}

func (JSONWriter) Write(path string, doc Document) {
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		panic(err)
	}
	file, err := os.Create(path)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	enc := json.NewEncoder(file)
	enc.SetIndent("", "  ")
	if err := enc.Encode(doc); err != nil {
		panic(err)
	}
}
