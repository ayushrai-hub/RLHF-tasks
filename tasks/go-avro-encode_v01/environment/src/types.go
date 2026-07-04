package main

// Schema is a parsed Avro schema node. Only the fields relevant to binary
// encoding are kept; names are retained for diagnostics but the encoding never
// depends on them.
type Schema struct {
	Type     string    // null boolean int long float double bytes string fixed enum record array map union
	Name     string    // record / enum / fixed
	Fields   []Field   // record: declared field order
	Items    *Schema   // array: element schema
	Values   *Schema   // map: value schema (keys are strings)
	Symbols  []string  // enum: declared symbol order
	Branches []*Schema // union: declared branch order
	Size     int       // fixed: number of bytes
}

// Field is one record field, in declaration order.
type Field struct {
	Name string
	Type *Schema
}

// Case is one encoding request: an Avro schema and a value, both as JSON.
type Case struct {
	ID     string          `json:"id"`
	Schema interface{}     `json:"schema"`
	Value  interface{}     `json:"value"`
}

// Input is the top-level stdin object.
type Input struct {
	Cases []Case `json:"cases"`
}

// CaseResult is the per-case output. On "ok", Hex is the lowercase hex of the
// Avro binary encoding. On "error" (the value does not conform to the schema, or
// the schema is not valid), Hex is "".
type CaseResult struct {
	ID     string `json:"id"`
	Status string `json:"status"`
	Hex    string `json:"hex"`
}

// Output is the top-level stdout object.
type Output struct {
	Cases []CaseResult `json:"cases"`
}
