#!/bin/bash
set -euo pipefail
set -x

# Oracle: build a from-scratch Go SPF evaluator into /app/spf-trace.

mkdir -p /app/spf /app/output

cat > /app/spf/main.go <<'GOEOF'
package main

import (
	"bufio"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"os"
	"sort"
	"strconv"
	"strings"
)

type dnsRR struct {
	A    []string `json:"A,omitempty"`
	AAAA []string `json:"AAAA,omitempty"`
	MX   [][2]any `json:"MX,omitempty"`
	TXT  []string `json:"TXT,omitempty"`
}

type message struct {
	ID       string `json:"id"`
	MailFrom string `json:"mail_from"`
	Helo     string `json:"helo"`
	FromIP   string `json:"from_ip"`
}

type policy struct {
	MaxLookups      int    `json:"max_lookups"`
	MaxVoidLookups  int    `json:"max_void_lookups"`
	MaxRedirectHops int    `json:"max_redirect_hops"`
	ReceivingDomain string `json:"receiving_domain"`
}

type verdict struct {
	ID          string   `json:"id"`
	Result      string   `json:"result"`
	Mechanism   string   `json:"mechanism"`
	Domain      string   `json:"domain"`
	Lookups     int      `json:"lookups"`
	VoidLookups int      `json:"void_lookups"`
	Trace       []string `json:"trace"`
}

type memoEntry struct {
	rr   dnsRR
	ok   bool
	void bool
}

type evalCtx struct {
	dns             map[string]dnsRR
	pol             policy
	msg             message
	lookups         int
	voidLookups     int
	trace           []string
	memo            map[string]memoEntry
	redirectVisited map[string]bool
}

func isIPv6(s string) bool {
	ip := net.ParseIP(s)
	if ip == nil {
		return false
	}
	return ip.To4() == nil && ip.To16() != nil
}

// classifyFamily returns "v4" for IPv4 or IPv4-mapped IPv6; "v6" for pure IPv6.
func classifyFamily(s string) string {
	ip := net.ParseIP(s)
	if ip == nil {
		return ""
	}
	if ip.To4() != nil {
		return "v4"
	}
	return "v6"
}

// v4Of returns the v4 form of an address that is either v4 or v4-mapped-v6.
func v4Of(s string) net.IP {
	ip := net.ParseIP(s)
	if ip == nil {
		return nil
	}
	return ip.To4()
}

func expandIPv6Nibbles(s string) string {
	ip := net.ParseIP(s)
	if ip == nil {
		return ""
	}
	ip16 := ip.To16()
	if ip16 == nil {
		return ""
	}
	var out []string
	for _, b := range ip16 {
		out = append(out, fmt.Sprintf("%x", b>>4))
		out = append(out, fmt.Sprintf("%x", b&0x0f))
	}
	return strings.Join(out, ".")
}

func (c *evalCtx) macroValue(letter byte, curDomain string) string {
	switch letter {
	case 's':
		return c.msg.MailFrom
	case 'l':
		if i := strings.LastIndex(c.msg.MailFrom, "@"); i >= 0 {
			return c.msg.MailFrom[:i]
		}
		return c.msg.MailFrom
	case 'o':
		if i := strings.LastIndex(c.msg.MailFrom, "@"); i >= 0 {
			return c.msg.MailFrom[i+1:]
		}
		return c.msg.MailFrom
	case 'd':
		return curDomain
	case 'i':
		fam := classifyFamily(c.msg.FromIP)
		if fam == "v6" {
			return expandIPv6Nibbles(c.msg.FromIP)
		}
		v4 := v4Of(c.msg.FromIP)
		if v4 != nil {
			return v4.String()
		}
		return c.msg.FromIP
	case 'h':
		return c.msg.Helo
	case 'r':
		return c.pol.ReceivingDomain
	}
	return ""
}

// parseMacroInner parses X<digits><r><delims> and returns letter, n (0=none), reverse, delims (map).
func parseMacroInner(inner string) (byte, int, bool, map[byte]bool, error) {
	if len(inner) == 0 {
		return 0, 0, false, nil, fmt.Errorf("empty macro")
	}
	letter := inner[0]
	rest := inner[1:]
	// digits
	i := 0
	for i < len(rest) && rest[i] >= '0' && rest[i] <= '9' {
		i++
	}
	digits := rest[:i]
	rest = rest[i:]
	// r flag
	reverse := false
	if len(rest) > 0 && (rest[0] == 'r' || rest[0] == 'R') {
		reverse = true
		rest = rest[1:]
	}
	// delimiter tail
	delims := map[byte]bool{'.': true}
	if len(rest) > 0 {
		delims = map[byte]bool{}
		for i := 0; i < len(rest); i++ {
			delims[rest[i]] = true
		}
	}
	n := 0
	if digits != "" {
		nv, err := strconv.Atoi(digits)
		if err != nil || nv < 1 {
			return 0, 0, false, nil, fmt.Errorf("bad digits")
		}
		n = nv
	}
	return letter, n, reverse, delims, nil
}

func splitOn(s string, delims map[byte]bool) []string {
	return strings.FieldsFunc(s, func(r rune) bool {
		if r > 127 {
			return false
		}
		return delims[byte(r)]
	})
}

func (c *evalCtx) expandMacros(s string, curDomain string) (string, error) {
	var b strings.Builder
	i := 0
	for i < len(s) {
		ch := s[i]
		if ch != '%' {
			b.WriteByte(ch)
			i++
			continue
		}
		if i+1 >= len(s) {
			return "", fmt.Errorf("dangling percent")
		}
		next := s[i+1]
		if next == '%' {
			b.WriteByte('%')
			i += 2
			continue
		}
		if next == '_' {
			b.WriteByte(' ')
			i += 2
			continue
		}
		if next == '-' {
			b.WriteString("%20")
			i += 2
			continue
		}
		if next != '{' {
			return "", fmt.Errorf("bad macro leader %%%c", next)
		}
		closeIdx := strings.Index(s[i:], "}")
		if closeIdx < 0 {
			return "", fmt.Errorf("unclosed macro")
		}
		inner := s[i+2 : i+closeIdx]
		i += closeIdx + 1
		letter, n, reverse, delims, err := parseMacroInner(inner)
		if err != nil {
			return "", err
		}
		raw := c.macroValue(letter, curDomain)
		labels := splitOn(raw, delims)
		if reverse {
			for a, b2 := 0, len(labels)-1; a < b2; a, b2 = a+1, b2-1 {
				labels[a], labels[b2] = labels[b2], labels[a]
			}
		}
		if n > 0 && n < len(labels) {
			labels = labels[len(labels)-n:]
		}
		b.WriteString(strings.Join(labels, "."))
	}
	return b.String(), nil
}

// countingLookup performs a memoized DNS lookup.
func (c *evalCtx) countingLookup(name string, rtype string) (dnsRR, bool, error) {
	key := strings.ToLower(name) + "|" + rtype
	if e, hit := c.memo[key]; hit {
		if e.void {
			return e.rr, false, nil
		}
		return e.rr, e.ok, nil
	}
	c.lookups++
	if c.lookups > c.pol.MaxLookups {
		return dnsRR{}, false, fmt.Errorf("permerror: max_lookups")
	}
	rr, ok := c.dns[strings.ToLower(name)]
	isVoid := false
	if !ok {
		isVoid = true
	} else {
		switch rtype {
		case "A", "AAAA":
			if len(rr.A) == 0 && len(rr.AAAA) == 0 {
				isVoid = true
			}
		case "MX":
			if len(rr.MX) == 0 {
				isVoid = true
			}
		case "TXT":
			if len(rr.TXT) == 0 {
				isVoid = true
			}
		}
	}
	if isVoid {
		c.voidLookups++
		if c.voidLookups > c.pol.MaxVoidLookups {
			c.memo[key] = memoEntry{rr: rr, ok: false, void: true}
			return dnsRR{}, false, fmt.Errorf("permerror: void")
		}
	}
	c.memo[key] = memoEntry{rr: rr, ok: ok && !isVoid, void: isVoid}
	return rr, ok && !isVoid, nil
}

// getSPFRecord scans TXT entries; returns permerror if >1 v=spf1 entries.
func (c *evalCtx) getSPFRecord(domain string) (string, bool, error) {
	rr, ok, err := c.countingLookup(domain, "TXT")
	if err != nil {
		return "", false, err
	}
	if !ok {
		return "", false, nil
	}
	var spf []string
	for _, t := range rr.TXT {
		if strings.HasPrefix(t, "v=spf1 ") || t == "v=spf1" {
			spf = append(spf, t)
		}
	}
	if len(spf) == 0 {
		return "", false, nil
	}
	if len(spf) > 1 {
		return "", false, fmt.Errorf("permerror: multiple v=spf1")
	}
	return spf[0], true, nil
}

func ipMatchCIDR(ipStr, cidr string, mechFamily string) bool {
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}
	_, ipnet, err := net.ParseCIDR(cidr)
	if err != nil {
		return false
	}
	// mechFamily is "v4" for ip4 mechanism, "v6" for ip6 mechanism.
	fam := classifyFamily(ipStr)
	if mechFamily == "v4" {
		if fam != "v4" {
			return false
		}
		v4 := v4Of(ipStr)
		if v4 == nil {
			return false
		}
		return ipnet.Contains(v4)
	}
	if mechFamily == "v6" {
		if fam != "v6" {
			return false
		}
		return ipnet.Contains(ip)
	}
	return false
}

func ipMatchAddr(ipStr, addr string, mechFamily string) bool {
	fam := classifyFamily(ipStr)
	afam := classifyFamily(addr)
	if fam != afam {
		return false
	}
	if mechFamily != "" && mechFamily != fam {
		return false
	}
	ip := net.ParseIP(ipStr)
	a := net.ParseIP(addr)
	if ip == nil || a == nil {
		return false
	}
	return ip.Equal(a)
}

func (c *evalCtx) parseTargetCIDR(arg, domain string) (string, string, error) {
	target := domain
	cidr := ""
	if arg == "" {
		return target, cidr, nil
	}
	if strings.HasPrefix(arg, ":") {
		body := arg[1:]
		if i := strings.Index(body, "/"); i >= 0 {
			target = body[:i]
			cidr = body[i:]
		} else {
			target = body
		}
	} else if strings.HasPrefix(arg, "/") {
		cidr = arg
	}
	if target == "" {
		return "", "", fmt.Errorf("permerror: empty target")
	}
	expanded, err := c.expandMacros(target, domain)
	if err != nil {
		return "", "", err
	}
	return expanded, cidr, nil
}

func toInt(v any) (int, bool) {
	switch x := v.(type) {
	case float64:
		return int(x), true
	case int:
		return x, true
	case string:
		n, err := strconv.Atoi(x)
		if err == nil {
			return n, true
		}
	}
	return 0, false
}

func qualToResult(q byte) string {
	switch q {
	case '+':
		return "pass"
	case '-':
		return "fail"
	case '~':
		return "softfail"
	case '?':
		return "neutral"
	}
	return "permerror"
}

// evalDomain returns result, mechanism-string, redirect-expanded-target, error.
// The redirect-expanded-target is the final redirect target visited that produced the terminal
// verdict (only non-empty at the level where the outer walk fell through to redirect).
func (c *evalCtx) evalDomain(domain string, depth int) (string, string, error) {
	c.trace = append(c.trace, "eval:"+strings.ToLower(domain))
	rec, ok, err := c.getSPFRecord(domain)
	if err != nil {
		return "permerror", "", err
	}
	if !ok {
		return "none", "", nil
	}
	body := strings.TrimPrefix(rec, "v=spf1")
	body = strings.TrimSpace(body)
	if body == "" {
		return "neutral", "", nil
	}
	terms := strings.Fields(body)

	var mechs []string
	var mechOrigs []string
	var redirect string
	hasAll := false
	for _, t := range terms {
		if strings.HasPrefix(t, "redirect=") {
			if redirect != "" {
				return "permerror", "", fmt.Errorf("permerror: duplicate redirect")
			}
			redirect = t[len("redirect="):]
			continue
		}
		if strings.HasPrefix(t, "exp=") {
			continue
		}
		if strings.Contains(t, "=") {
			return "permerror", "", fmt.Errorf("permerror: unknown modifier %s", t)
		}
		mechs = append(mechs, t)
		mechOrigs = append(mechOrigs, t)
		bare := t
		if len(bare) > 0 && (bare[0] == '+' || bare[0] == '-' || bare[0] == '~' || bare[0] == '?') {
			bare = bare[1:]
		}
		if bare == "all" {
			hasAll = true
		}
	}

	for idx, m := range mechs {
		orig := mechOrigs[idx]
		qual := byte('+')
		hadExplicit := false
		if len(m) > 0 && (m[0] == '+' || m[0] == '-' || m[0] == '~' || m[0] == '?') {
			qual = m[0]
			m = m[1:]
			hadExplicit = true
		}
		unexpandedToken := orig
		if !hadExplicit {
			unexpandedToken = "+" + orig
		}
		name := m
		arg := ""
		if i := strings.IndexAny(m, ":/"); i >= 0 {
			name = m[:i]
			arg = m[i:]
		}
		matched := false
		switch name {
		case "all":
			matched = true
		case "ip4":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("permerror: bad ip4 arg")
			}
			val := arg[1:]
			if strings.Contains(val, "/") {
				matched = ipMatchCIDR(c.msg.FromIP, val, "v4")
			} else {
				matched = ipMatchAddr(c.msg.FromIP, val, "v4")
			}
		case "ip6":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("permerror: bad ip6 arg")
			}
			val := arg[1:]
			if strings.Contains(val, "/") {
				matched = ipMatchCIDR(c.msg.FromIP, val, "v6")
			} else {
				matched = ipMatchAddr(c.msg.FromIP, val, "v6")
			}
		case "a":
			target, cidr, err := c.parseTargetCIDR(arg, domain)
			if err != nil {
				return "permerror", "", err
			}
			rr, ok, err := c.countingLookup(target, "A")
			if err != nil {
				return "permerror", "", err
			}
			if ok {
				addrs := append([]string{}, rr.A...)
				addrs = append(addrs, rr.AAAA...)
				fam := classifyFamily(c.msg.FromIP)
				for _, a := range addrs {
					afam := classifyFamily(a)
					if fam != afam {
						continue
					}
					if cidr != "" {
						matched = ipMatchCIDR(c.msg.FromIP, a+cidr, fam)
					} else {
						matched = ipMatchAddr(c.msg.FromIP, a, fam)
					}
					if matched {
						break
					}
				}
			}
		case "mx":
			target, cidr, err := c.parseTargetCIDR(arg, domain)
			if err != nil {
				return "permerror", "", err
			}
			rr, ok, err := c.countingLookup(target, "MX")
			if err != nil {
				return "permerror", "", err
			}
			if ok {
				mxs := make([][2]any, len(rr.MX))
				copy(mxs, rr.MX)
				sort.SliceStable(mxs, func(i, j int) bool {
					pi, _ := toInt(mxs[i][0])
					pj, _ := toInt(mxs[j][0])
					return pi < pj
				})
				fam := classifyFamily(c.msg.FromIP)
				for _, mx := range mxs {
					host, _ := mx[1].(string)
					rr2, ok2, err := c.countingLookup(host, "A")
					if err != nil {
						return "permerror", "", err
					}
					if !ok2 {
						continue
					}
					addrs := append([]string{}, rr2.A...)
					addrs = append(addrs, rr2.AAAA...)
					for _, a := range addrs {
						afam := classifyFamily(a)
						if fam != afam {
							continue
						}
						if cidr != "" {
							matched = ipMatchCIDR(c.msg.FromIP, a+cidr, fam)
						} else {
							matched = ipMatchAddr(c.msg.FromIP, a, fam)
						}
						if matched {
							break
						}
					}
					if matched {
						break
					}
				}
			}
		case "include":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("permerror: include needs :")
			}
			spec := arg[1:]
			expanded, err := c.expandMacros(spec, domain)
			if err != nil {
				return "permerror", "", err
			}
			if depth+1 > c.pol.MaxRedirectHops {
				return "permerror", "", fmt.Errorf("permerror: include depth")
			}
			sub, _, err := c.evalDomain(expanded, depth+1)
			if err != nil {
				return sub, "", err
			}
			switch sub {
			case "pass":
				matched = true
			case "none":
				return "permerror", "", fmt.Errorf("permerror: include target none")
			case "temperror":
				return "temperror", "", nil
			case "permerror":
				return "permerror", "", nil
			default:
				matched = false
			}
		case "exists":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("permerror: exists needs :")
			}
			spec := arg[1:]
			expanded, err := c.expandMacros(spec, domain)
			if err != nil {
				return "permerror", "", err
			}
			rr, ok, err := c.countingLookup(expanded, "A")
			if err != nil {
				return "permerror", "", err
			}
			if ok && len(rr.A) > 0 {
				matched = true
			}
		default:
			return "permerror", "", fmt.Errorf("permerror: unknown mechanism %s", name)
		}
		if matched {
			c.trace = append(c.trace, unexpandedToken)
			return qualToResult(qual), unexpandedToken, nil
		}
	}
	if redirect != "" && !hasAll {
		expanded, err := c.expandMacros(redirect, domain)
		if err != nil {
			return "permerror", "", err
		}
		lowerExp := strings.ToLower(expanded)
		if c.redirectVisited[lowerExp] {
			return "permerror", "", fmt.Errorf("permerror: redirect loop")
		}
		c.redirectVisited[lowerExp] = true
		sub, _, err := c.evalDomain(expanded, depth+1)
		if err != nil {
			return sub, "", err
		}
		if sub == "none" {
			return "permerror", "", fmt.Errorf("permerror: redirect target none")
		}
		return sub, "redirect=" + expanded, nil
	}
	return "neutral", "", nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	dataDir := "/app/data"
	outDir := "/app/output"
	if v := os.Getenv("SPF_DATA_DIR"); v != "" {
		dataDir = v
	}
	if v := os.Getenv("SPF_OUT_DIR"); v != "" {
		outDir = v
	}
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	dnsRaw, err := os.ReadFile(dataDir + "/dns.json")
	if err != nil {
		return err
	}
	var dns map[string]dnsRR
	if err := json.Unmarshal(dnsRaw, &dns); err != nil {
		return err
	}
	polRaw, err := os.ReadFile(dataDir + "/policy.json")
	if err != nil {
		return err
	}
	var pol policy
	if err := json.Unmarshal(polRaw, &pol); err != nil {
		return err
	}
	f, err := os.Open(dataDir + "/messages.jsonl")
	if err != nil {
		return err
	}
	defer f.Close()
	verdictsFile, err := os.Create(outDir + "/verdicts.ndjson")
	if err != nil {
		return err
	}
	defer verdictsFile.Close()
	counts := map[string]int{}
	total := 0
	// chain digest accumulator
	acc := make([]byte, 32)
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 0, 1024*1024), 4*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var msg message
		if err := json.Unmarshal([]byte(line), &msg); err != nil {
			return err
		}
		domain := msg.MailFrom
		if i := strings.LastIndex(domain, "@"); i >= 0 {
			domain = domain[i+1:]
		}
		domain = strings.ToLower(domain)
		ctx := &evalCtx{
			dns:             dns,
			pol:             pol,
			msg:             msg,
			memo:            map[string]memoEntry{},
			redirectVisited: map[string]bool{},
		}
		result, mech, _ := ctx.evalDomain(domain, 0)
		v := verdict{
			ID:          msg.ID,
			Result:      result,
			Mechanism:   mech,
			Domain:      domain,
			Lookups:     ctx.lookups,
			VoidLookups: ctx.voidLookups,
			Trace:       ctx.trace,
		}
		if v.Trace == nil {
			v.Trace = []string{}
		}
		enc, _ := json.Marshal(v)
		verdictsFile.Write(enc)
		verdictsFile.Write([]byte("\n"))
		counts[result]++
		total++
		// fold into chain digest
		line6 := msg.ID + "|" + result + "|" + mech + "|" + domain + "|" + strconv.Itoa(ctx.lookups) + "|" + strconv.Itoa(ctx.voidLookups)
		h := sha256.New()
		h.Write(acc)
		h.Write([]byte(line6))
		acc = h.Sum(nil)
	}
	if err := scanner.Err(); err != nil && err != io.EOF {
		return err
	}
	// Ordered summary with insertion-order preservation via manual JSON build.
	keys := []string{"pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"}
	var buf bytes.Buffer
	buf.WriteString("{\n")
	buf.WriteString("  \"total\": " + strconv.Itoa(total) + ",\n")
	buf.WriteString("  \"counts\": {\n")
	for i, k := range keys {
		suffix := ","
		if i == len(keys)-1 {
			suffix = ""
		}
		buf.WriteString("    \"" + k + "\": " + strconv.Itoa(counts[k]) + suffix + "\n")
	}
	buf.WriteString("  },\n")
	buf.WriteString("  \"chain_digest\": \"" + hex.EncodeToString(acc) + "\"\n")
	buf.WriteString("}\n")
	if err := os.WriteFile(outDir+"/summary.json", buf.Bytes(), 0o644); err != nil {
		return err
	}
	return nil
}
GOEOF

cd /app/spf
go build -o /app/spf-trace .
/app/spf-trace
