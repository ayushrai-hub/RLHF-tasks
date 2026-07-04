// Package model parses the sequential layer description that the checkpoint
// planner operates on.
package model

import (
	"bufio"
	"fmt"
	"io"
	"strconv"
	"strings"
)

// Layer is one layer of the ordered network. Activation is the activation
// memory the layer holds when its output is retained as a checkpoint;
// Recompute is the cost charged to regenerate this layer's activation during
// the backward pass when it was not retained.
type Layer struct {
	Activation int
	Recompute  int
}

// Parse reads one layer per line from r. Each non-empty line has two
// non-negative integers: the activation memory and the recompute cost, in that
// order. Blank lines are ignored.
func Parse(r io.Reader) ([]Layer, error) {
	var layers []Layer
	scanner := bufio.NewScanner(r)
	scanner.Buffer(make([]byte, 0, 1024*1024), 16*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) != 2 {
			return nil, fmt.Errorf("a layer line needs exactly two values")
		}
		act, err := strconv.Atoi(fields[0])
		if err != nil || act < 0 {
			return nil, fmt.Errorf("bad activation memory %q", fields[0])
		}
		rec, err := strconv.Atoi(fields[1])
		if err != nil || rec < 0 {
			return nil, fmt.Errorf("bad recompute cost %q", fields[1])
		}
		layers = append(layers, Layer{Activation: act, Recompute: rec})
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	if len(layers) == 0 {
		return nil, fmt.Errorf("no layers given")
	}
	return layers, nil
}
