package main

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

// Scenario names one matrix row from matrix_order.txt.
type Scenario struct {
	Name string
}

// LoadScenarios reads scenario identifiers in file order.
func LoadScenarios(fixturesRoot string) ([]Scenario, error) {
	path := filepath.Join(fixturesRoot, "matrix_order.txt")
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var out []Scenario
	scan := bufio.NewScanner(f)
	for scan.Scan() {
		line := strings.TrimSpace(scan.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		out = append(out, Scenario{Name: line})
	}
	if err := scan.Err(); err != nil {
		return nil, err
	}
	if len(out) == 0 {
		return nil, fmt.Errorf("driver: empty scenario matrix")
	}
	return out, nil
}
