package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
)

// main reads one Input object from stdin and writes one Output object to
// stdout. Each case is encoded independently. This file is the program's stable
// entry point.
func main() {
	raw, err := io.ReadAll(os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, "read stdin:", err)
		os.Exit(1)
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	var in Input
	if err := dec.Decode(&in); err != nil {
		fmt.Fprintln(os.Stderr, "parse input:", err)
		os.Exit(1)
	}

	out := Output{Cases: make([]CaseResult, 0, len(in.Cases))}
	for _, c := range in.Cases {
		out.Cases = append(out.Cases, encodeCase(c))
	}

	enc := json.NewEncoder(os.Stdout)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(out); err != nil {
		fmt.Fprintln(os.Stderr, "encode output:", err)
		os.Exit(1)
	}
}

// encodeCase parses the schema, encodes the value against it, and shapes the
// result. A schema that does not parse or a value that does not conform to the
// schema yields status "error".
func encodeCase(c Case) CaseResult {
	res := CaseResult{ID: c.ID, Status: "error", Hex: ""}
	s, err := parseSchema(c.Schema)
	if err != nil {
		return res
	}
	b, err := encode(s, c.Value)
	if err != nil {
		return res
	}
	res.Status = "ok"
	res.Hex = hex.EncodeToString(b)
	return res
}
