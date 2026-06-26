// Legacy v0 gateway token checker.
//
// This is the checker the old gateway still runs in production. It is reproduced
// here verbatim for reference during the v0 -> v1 migration. The 32-byte server
// key lives only on the gateway; here it is read from $WARDEN_V0_KEY so this copy
// can be exercised in a controlled setting. Do not commit the key.
//
// Usage:
//
//	WARDEN_V0_KEY=<64 hex chars> go run verify.go <token> --path <p> --now <unix>
//
// Exits 0 if the token is valid and authorizes the path, 1 otherwise.
package main

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"os"
	"strconv"
	"strings"
)

func serverKey() []byte {
	k, err := hex.DecodeString(os.Getenv("WARDEN_V0_KEY"))
	if err != nil || len(k) != 32 {
		fmt.Fprintln(os.Stderr, "WARDEN_V0_KEY must be 32 bytes of hex")
		os.Exit(2)
	}
	return k
}

func segments(p string) []string {
	out := []string{}
	for _, s := range strings.Split(p, "/") {
		if s != "" {
			out = append(out, s)
		}
	}
	return out
}

// contains reports whether scope is at or above req by path segments.
func contains(scope, req string) bool {
	ss, rs := segments(scope), segments(req)
	if len(rs) < len(ss) {
		return false
	}
	for i := range ss {
		if ss[i] != rs[i] {
			return false
		}
	}
	return true
}

func printableASCII(b []byte) bool {
	for _, c := range b {
		if c < 0x20 || c > 0x7e {
			return false
		}
	}
	return true
}

// scan returns the last valid scope= and exp= directives in the body.
func scan(body []byte) (scope string, exp int64, haveScope, haveExp bool) {
	for _, line := range strings.Split(string(body), "\n") {
		lb := []byte(line)
		if !printableASCII(lb) {
			continue
		}
		if strings.HasPrefix(line, "scope=") && strings.HasPrefix(line[6:], "/") {
			scope, haveScope = line[6:], true
		} else if strings.HasPrefix(line, "exp=") {
			if n, err := strconv.ParseInt(line[4:], 10, 64); err == nil {
				exp, haveExp = n, true
			}
		}
	}
	return
}

func main() {
	args := os.Args[1:]
	var token, path string
	var now int64
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--path":
			i++
			path = args[i]
		case "--now":
			i++
			now, _ = strconv.ParseInt(args[i], 10, 64)
		default:
			token = args[i]
		}
	}
	parts := strings.Split(strings.TrimSpace(token), ".")
	if len(parts) != 3 || parts[0] != "v0" {
		fmt.Fprintln(os.Stderr, "reject: malformed v0 token")
		os.Exit(1)
	}
	body, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		fmt.Fprintln(os.Stderr, "reject: bad body encoding")
		os.Exit(1)
	}
	tag, err := hex.DecodeString(parts[2])
	if err != nil || len(tag) != 32 {
		fmt.Fprintln(os.Stderr, "reject: bad tag")
		os.Exit(1)
	}
	want := sha256.Sum256(append(serverKey(), body...))
	if subtle.ConstantTimeCompare(want[:], tag) != 1 {
		fmt.Fprintln(os.Stderr, "reject: signature mismatch")
		os.Exit(1)
	}
	scope, exp, haveScope, haveExp := scan(body)
	if !haveScope {
		fmt.Fprintln(os.Stderr, "reject: no scope")
		os.Exit(1)
	}
	if !haveExp || !(now < exp) {
		fmt.Fprintln(os.Stderr, "reject: expired")
		os.Exit(1)
	}
	if !contains(scope, path) {
		fmt.Fprintln(os.Stderr, "reject: path not in scope")
		os.Exit(1)
	}
	fmt.Printf("accept scope=%s\n", scope)
}
