// Command warden is a capability-token ("sigil") authorization tool.
//
// See SPEC.md for the wire formats and rules. It implements the v1 token: verify
// (including third-party caveats discharged by bound discharge sigils), mint,
// attenuate, discharge, and bind.
package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"fmt"
	"os"
	"strconv"
	"strings"
)

var b64 = base64.RawURLEncoding

var (
	dsID   = []byte("sigil/v1\x00id\x00")
	dsCav  = []byte("sigil/v1\x00cav\x00")
	dsCK   = []byte("sigil/v1\x00ck\x00")
	dsCID  = []byte("sigil/v1\x00cid\x00")
	dsVID  = []byte("sigil/v1\x00vid\x00")
	dsBind = []byte("sigil/v1\x00bind\x00")
)

func die(code int, format string, a ...any) {
	fmt.Fprintf(os.Stderr, format+"\n", a...)
	os.Exit(code)
}

func reject(msg string) {
	fmt.Fprintln(os.Stderr, "reject: "+msg)
	os.Exit(1)
}

// ---- primitives ------------------------------------------------------------
func concat(parts ...[]byte) []byte {
	var out []byte
	for _, p := range parts {
		out = append(out, p...)
	}
	return out
}

func mac(key, msg []byte) []byte {
	h := hmac.New(sha256.New, key)
	h.Write(msg)
	return h.Sum(nil)
}

func ks(parts ...[]byte) []byte {
	s := sha256.Sum256(concat(parts...))
	return s[:]
}

func xor(a, b []byte) []byte {
	out := make([]byte, len(a))
	for i := range a {
		out[i] = a[i] ^ b[i]
	}
	return out
}

func mustHex(s string) []byte {
	b, err := hex.DecodeString(s)
	if err != nil {
		die(2, "bad hex value")
	}
	return b
}

// ---- v1 encode/parse -------------------------------------------------------
func encode(prefix string, idBytes []byte, cavs [][]byte, tag []byte) string {
	enc := make([]string, len(cavs))
	for i, c := range cavs {
		enc[i] = b64.EncodeToString(c)
	}
	return prefix + "." + b64.EncodeToString(idBytes) + "." + strings.Join(enc, "~") + "." + b64.EncodeToString(tag)
}

type parsed struct {
	id   []byte
	cavs [][]byte
	tag  []byte
}

func parseToken(s, prefix string) (*parsed, error) {
	p := strings.Split(s, ".")
	if len(p) != 4 || p[0] != prefix {
		return nil, fmt.Errorf("not a %s token", prefix)
	}
	id, err := b64.DecodeString(p[1])
	if err != nil {
		return nil, fmt.Errorf("bad base64 id")
	}
	var cavs [][]byte
	if p[2] != "" {
		for _, x := range strings.Split(p[2], "~") {
			c, err := b64.DecodeString(x)
			if err != nil {
				return nil, fmt.Errorf("bad base64 caveat")
			}
			cavs = append(cavs, c)
		}
	}
	tag, err := b64.DecodeString(p[3])
	if err != nil {
		return nil, fmt.Errorf("bad base64 tag")
	}
	return &parsed{id, cavs, tag}, nil
}

// thirdCaveat builds a third-party caveat raw string from the spec loc|pred|tpkeyhex.
func thirdCaveat(currentSig []byte, spec string) []byte {
	f := strings.SplitN(spec, "|", 3)
	if len(f) != 3 {
		die(2, "bad --third (want location|predicate|tpkeyhex)")
	}
	loc, pred, tpk := f[0], f[1], mustHex(f[2])
	pb := []byte(pred)
	cK := ks(dsCK, tpk, currentSig, pb)
	vid := xor(cK, ks(dsVID, currentSig))
	cid := xor(cK, ks(dsCID, tpk, pb))
	return []byte("third=" + loc + "|" + pred + "|" + b64.EncodeToString(cid) + "|" + b64.EncodeToString(vid))
}

// ---- predicate helpers -----------------------------------------------------
func segs(p string) []string {
	out := []string{}
	for _, s := range strings.Split(p, "/") {
		if s != "" {
			out = append(out, s)
		}
	}
	return out
}

func pathWithin(prefix, req string) bool {
	ps, rs := segs(prefix), segs(req)
	if len(rs) < len(ps) {
		return false
	}
	for i := range ps {
		if rs[i] != ps[i] {
			return false
		}
	}
	return true
}

func ipv4ToInt(ip string) (uint32, error) {
	o := strings.Split(ip, ".")
	if len(o) != 4 {
		return 0, fmt.Errorf("bad ipv4")
	}
	var n uint32
	for _, part := range o {
		if part == "" || (len(part) > 1 && part[0] == '0') {
			return 0, fmt.Errorf("bad octet")
		}
		v, err := strconv.Atoi(part)
		if err != nil || v < 0 || v > 255 {
			return 0, fmt.Errorf("bad octet")
		}
		n = (n << 8) | uint32(v)
	}
	return n, nil
}

func ipInCIDR(ip, cidr string) (bool, error) {
	sl := strings.SplitN(cidr, "/", 2)
	if len(sl) != 2 {
		return false, fmt.Errorf("bad cidr")
	}
	bits, err := strconv.Atoi(sl[1])
	if err != nil || bits < 0 || bits > 32 {
		return false, fmt.Errorf("bad cidr")
	}
	var mask uint32
	if bits != 0 {
		mask = (0xFFFFFFFF << (32 - bits)) & 0xFFFFFFFF
	}
	a, err := ipv4ToInt(ip)
	if err != nil {
		return false, err
	}
	b, err := ipv4ToInt(sl[0])
	if err != nil {
		return false, err
	}
	return (a & mask) == (b & mask), nil
}

type ctx struct {
	now              int64
	path, method, ip string
	hasNow, hasPath  bool
	hasMethod, hasIP bool
}

func betterScope(a, b string) bool { return len(segs(a)) > len(segs(b)) }

// evalFirsts evaluates first-party caveats against ctx, returns effective scope.
func evalFirsts(cavs [][]byte, c ctx) string {
	scope := "/"
	for _, raw := range cavs {
		for _, by := range raw {
			if by < 0x20 || by > 0x7E {
				reject("non-ascii caveat")
			}
		}
		s := string(raw)
		eq := strings.IndexByte(s, '=')
		if eq < 0 {
			reject("malformed caveat")
		}
		typ, arg := s[:eq], s[eq+1:]
		switch typ {
		case "exp":
			if !c.hasNow {
				reject("exp requires now")
			}
			v, err := strconv.ParseInt(arg, 10, 64)
			if err != nil {
				reject("malformed caveat argument")
			}
			if !(c.now < v) {
				reject("expired")
			}
		case "nbf":
			if !c.hasNow {
				reject("nbf requires now")
			}
			v, err := strconv.ParseInt(arg, 10, 64)
			if err != nil {
				reject("malformed caveat argument")
			}
			if !(c.now >= v) {
				reject("not yet valid")
			}
		case "path":
			if !c.hasPath {
				reject("path caveat requires path")
			}
			if !pathWithin(arg, c.path) {
				reject("path not authorized")
			}
			if betterScope(arg, scope) {
				scope = arg
			}
		case "method":
			if !c.hasMethod {
				reject("method caveat requires method")
			}
			ok := false
			for _, m := range strings.Split(arg, ",") {
				if m != "" && strings.EqualFold(m, c.method) {
					ok = true
				}
			}
			if !ok {
				reject("method not authorized")
			}
		case "cidr":
			if !c.hasIP {
				reject("cidr caveat requires ip")
			}
			in, err := ipInCIDR(c.ip, arg)
			if err != nil {
				reject("malformed caveat argument")
			}
			if !in {
				reject("ip not authorized")
			}
		default:
			reject("unknown caveat type: " + typ)
		}
	}
	return scope
}

func verify(rootKey []byte, t *parsed, c ctx, discharges []string) {
	sig := mac(rootKey, concat(dsID, t.id))
	var firsts [][]byte
	type third struct {
		cid string
		cK  []byte
	}
	var thirds []third
	for _, raw := range t.cavs {
		cur := sig
		if strings.HasPrefix(string(raw), "third=") {
			body := string(raw[len("third="):])
			f := strings.Split(body, "|")
			if len(f) != 4 {
				reject("malformed third-party caveat")
			}
			vid, err := b64.DecodeString(f[3])
			if err != nil {
				reject("malformed third-party caveat")
			}
			thirds = append(thirds, third{f[2], xor(vid, ks(dsVID, cur))})
		} else {
			firsts = append(firsts, raw)
		}
		sig = mac(cur, concat(dsCav, raw))
	}
	if subtle.ConstantTimeCompare(sig, t.tag) != 1 {
		reject("bad signature")
	}
	rootTag := t.tag
	scope := evalFirsts(firsts, c)
	dmap := map[string]*parsed{}
	for _, d := range discharges {
		dp, err := parseToken(strings.TrimSpace(d), "disch")
		if err != nil {
			reject("malformed discharge")
		}
		dmap[b64.EncodeToString(dp.id)] = dp
	}
	for _, th := range thirds {
		dp, ok := dmap[th.cid]
		if !ok {
			reject("missing discharge")
		}
		osig := mac(th.cK, concat(dsID, dp.id))
		for _, cv := range dp.cavs {
			osig = mac(osig, concat(dsCav, cv))
		}
		if subtle.ConstantTimeCompare(dp.tag, mac(rootTag, concat(dsBind, osig))) != 1 {
			reject("bad discharge binding")
		}
		evalFirsts(dp.cavs, c)
	}
	fmt.Printf("OK %s\n", scope)
}

// ---- argument parsing ------------------------------------------------------
func parseArgs(args []string, repeatable map[string]bool) (map[string]string, map[string][]string, []string) {
	flags := map[string]string{}
	reps := map[string][]string{}
	var pos []string
	for i := 0; i < len(args); {
		a := args[i]
		if strings.HasPrefix(a, "--") {
			name := a[2:]
			if i+1 >= len(args) {
				die(2, "missing value for --%s", name)
			}
			val := args[i+1]
			if repeatable[name] {
				reps[name] = append(reps[name], val)
			} else {
				flags[name] = val
			}
			i += 2
		} else {
			pos = append(pos, a)
			i++
		}
	}
	return flags, reps, pos
}

func mustKey(flags map[string]string) []byte {
	h, ok := flags["key"]
	if !ok {
		die(2, "missing --key")
	}
	return mustHex(h)
}

func readToken(pos []string) string {
	if len(pos) < 1 {
		die(2, "missing token argument")
	}
	if pos[0] == "-" {
		var sb strings.Builder
		buf := make([]byte, 4096)
		for {
			n, err := os.Stdin.Read(buf)
			sb.Write(buf[:n])
			if n == 0 || err != nil {
				break
			}
		}
		return strings.TrimSpace(sb.String())
	}
	return strings.TrimSpace(pos[0])
}

func chainCaveats(sig []byte, firstCaveats, thirds []string) ([]byte, [][]byte) {
	var cavs [][]byte
	for _, c := range firstCaveats {
		cb := []byte(c)
		sig = mac(sig, concat(dsCav, cb))
		cavs = append(cavs, cb)
	}
	for _, spec := range thirds {
		raw := thirdCaveat(sig, spec)
		sig = mac(sig, concat(dsCav, raw))
		cavs = append(cavs, raw)
	}
	return sig, cavs
}

func main() {
	if len(os.Args) < 2 {
		die(2, "usage: warden <verify|mint|attenuate|discharge|bind> ...")
	}
	args := os.Args[2:]
	switch os.Args[1] {
	case "verify":
		flags, reps, pos := parseArgs(args, map[string]bool{"discharge": true})
		key := mustKey(flags)
		tk, err := parseToken(readToken(pos), "v1")
		if err != nil {
			reject("malformed: " + err.Error())
		}
		c := ctx{}
		if v, ok := flags["now"]; ok {
			n, err := strconv.ParseInt(v, 10, 64)
			if err != nil {
				die(2, "bad --now")
			}
			c.now, c.hasNow = n, true
		}
		if v, ok := flags["path"]; ok {
			c.path, c.hasPath = v, true
		}
		if v, ok := flags["method"]; ok {
			c.method, c.hasMethod = v, true
		}
		if v, ok := flags["ip"]; ok {
			c.ip, c.hasIP = v, true
		}
		verify(key, tk, c, reps["discharge"])
	case "mint":
		flags, reps, _ := parseArgs(args, map[string]bool{"caveat": true, "third": true})
		key := mustKey(flags)
		id, ok := flags["id"]
		if !ok {
			die(2, "missing --id")
		}
		idb := []byte(id)
		sig, cavs := chainCaveats(mac(key, concat(dsID, idb)), reps["caveat"], reps["third"])
		fmt.Println(encode("v1", idb, cavs, sig))
	case "attenuate":
		_, reps, pos := parseArgs(args, map[string]bool{"caveat": true, "third": true})
		tk, err := parseToken(readToken(pos), "v1")
		if err != nil {
			die(2, "malformed token: %v", err)
		}
		sig, added := chainCaveats(tk.tag, reps["caveat"], reps["third"])
		fmt.Println(encode("v1", tk.id, append(tk.cavs, added...), sig))
	case "discharge":
		flags, reps, _ := parseArgs(args, map[string]bool{"caveat": true})
		tpk := mustHex(flags["tpkey"])
		cid, err := b64.DecodeString(flags["cid"])
		if err != nil {
			die(2, "bad --cid")
		}
		cK := xor(cid, ks(dsCID, tpk, []byte(flags["predicate"])))
		sig, cavs := chainCaveats(mac(cK, concat(dsID, cid)), reps["caveat"], nil)
		fmt.Println(encode("disch", cid, cavs, sig))
	case "bind":
		_, _, pos := parseArgs(args, nil)
		if len(pos) < 2 {
			die(2, "usage: warden bind <root-token> <discharge>")
		}
		root, err := parseToken(strings.TrimSpace(pos[0]), "v1")
		if err != nil {
			die(2, "bad root token")
		}
		dp := strings.Split(strings.TrimSpace(pos[1]), ".")
		if len(dp) != 4 || dp[0] != "disch" {
			die(2, "bad discharge")
		}
		orig, err := b64.DecodeString(dp[3])
		if err != nil {
			die(2, "bad discharge tag")
		}
		bound := mac(root.tag, concat(dsBind, orig))
		fmt.Println(dp[0] + "." + dp[1] + "." + dp[2] + "." + b64.EncodeToString(bound))
	default:
		die(2, "unknown command: %s", os.Args[1])
	}
}
