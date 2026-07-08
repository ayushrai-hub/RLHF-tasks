// Package loader reads the input ledger and writes the output plan.
package loader

import (
	"encoding/json"
	"os"
)

func readJSON(path string, v interface{}) error {
	b, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, v)
}
