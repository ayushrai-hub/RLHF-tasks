package modfile

import "fmt"

// Parse reads the bytes of a go.mod file into a File. It must understand the
// module and go directives, require directives in both the single-line and
// parenthesised block forms, and the replace and exclude directives in both
// forms. It strips comments, records // indirect markers, and tolerates the
// older dialect that double-quotes paths and versions. The replace grammar is
// "old [oldversion] => new newversion" with the => arrow; exclude is
// "path version". See docs/spec.md for the grammar the resolver depends on and
// the File fields these directives populate.
//
// STUB: returns a not_implemented error. Implement the parser.
func Parse(data []byte) (*File, error) {
	return nil, fmt.Errorf("not_implemented")
}
