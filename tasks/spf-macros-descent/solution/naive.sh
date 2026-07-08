#!/bin/bash
# NAIVE twin: transcribes docs literally but misses:
# - custom macro delimiter tail (uses only "." as delimiter)
# - IPv4-mapped IPv6 family classification (treats ::ffff:v4 as v6)
# - multiple v=spf1 records (picks first, no permerror)
# - lookup memoization (every call counts)
# - redirect loop guard (relies only on lookup budget to break loops)
# - include depth guard (relies only on lookup budget)
# - chain_digest field (omits it)
# - unexpanded mechanism preservation (writes expanded target inside mechanism field)
# Used ONLY for the naive-twin gate; never copied into the image.
set -euo pipefail
set -x

mkdir -p /app/spf /app/output

cat > /app/spf/main.go <<'GOEOF'
package main

import (
	"bufio"
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

type evalCtx struct {
	dns         map[string]dnsRR
	pol         policy
	msg         message
	lookups     int
	voidLookups int
	trace       []string
}

func isIPv6(s string) bool {
	ip := net.ParseIP(s)
	if ip == nil {
		return false
	}
	return ip.To4() == nil && ip.To16() != nil
}

func expandIPv6Nibbles(s string) string {
	ip16 := net.ParseIP(s).To16()
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
		if isIPv6(c.msg.FromIP) {
			return expandIPv6Nibbles(c.msg.FromIP)
		}
		return c.msg.FromIP
	case 'h':
		return c.msg.Helo
	case 'r':
		return c.pol.ReceivingDomain
	}
	return ""
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
			return "", fmt.Errorf("bad leader")
		}
		closeIdx := strings.Index(s[i:], "}")
		if closeIdx < 0 {
			return "", fmt.Errorf("unclosed")
		}
		inner := s[i+2 : i+closeIdx]
		i += closeIdx + 1
		if len(inner) == 0 {
			return "", fmt.Errorf("empty macro")
		}
		letter := inner[0]
		rest := inner[1:]
		// NAIVE: only digits and r; NO custom delimiters.
		digits := ""
		reverse := false
		for j := 0; j < len(rest); j++ {
			r := rest[j]
			if r >= '0' && r <= '9' {
				digits += string(r)
			} else if r == 'r' || r == 'R' {
				reverse = true
			}
		}
		raw := c.macroValue(letter, curDomain)
		labels := strings.Split(raw, ".") // NAIVE: only "." delimiter
		if reverse {
			for a, b2 := 0, len(labels)-1; a < b2; a, b2 = a+1, b2-1 {
				labels[a], labels[b2] = labels[b2], labels[a]
			}
		}
		if digits != "" {
			n, _ := strconv.Atoi(digits)
			if n > 0 && n < len(labels) {
				labels = labels[len(labels)-n:]
			}
		}
		b.WriteString(strings.Join(labels, "."))
	}
	return b.String(), nil
}

func (c *evalCtx) countingLookup(name string, rtype string) (dnsRR, bool, error) {
	// NAIVE: no memo.
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
			return dnsRR{}, false, fmt.Errorf("permerror: void")
		}
	}
	return rr, ok && !isVoid, nil
}

func (c *evalCtx) getSPFRecord(domain string) (string, bool, error) {
	rr, ok, err := c.countingLookup(domain, "TXT")
	if err != nil {
		return "", false, err
	}
	if !ok {
		return "", false, nil
	}
	// NAIVE: picks first v=spf1 without checking for multiple.
	for _, t := range rr.TXT {
		if strings.HasPrefix(t, "v=spf1 ") || t == "v=spf1" {
			return t, true, nil
		}
	}
	return "", false, nil
}

func ipMatchCIDR(ipStr, cidr string) bool {
	// NAIVE: no family classification for v4-mapped v6.
	ip := net.ParseIP(ipStr)
	if ip == nil {
		return false
	}
	_, ipnet, err := net.ParseCIDR(cidr)
	if err != nil {
		return false
	}
	return ipnet.Contains(ip)
}

func ipMatchAddr(ipStr, addr string) bool {
	ip := net.ParseIP(ipStr)
	a := net.ParseIP(addr)
	if ip == nil || a == nil {
		return false
	}
	return ip.Equal(a)
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
		return "", "", fmt.Errorf("empty")
	}
	exp, err := c.expandMacros(target, domain)
	if err != nil {
		return "", "", err
	}
	return exp, cidr, nil
}

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
	var redirect string
	for _, t := range terms {
		if strings.HasPrefix(t, "redirect=") {
			redirect = t[len("redirect="):]
			continue
		}
		if strings.HasPrefix(t, "exp=") {
			continue
		}
		if strings.Contains(t, "=") {
			return "permerror", "", fmt.Errorf("modifier")
		}
		mechs = append(mechs, t)
	}
	// NAIVE: does not check hasAll for redirect gating.

	for _, m := range mechs {
		qual := byte('+')
		if len(m) > 0 && (m[0] == '+' || m[0] == '-' || m[0] == '~' || m[0] == '?') {
			qual = m[0]
			m = m[1:]
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
				return "permerror", "", fmt.Errorf("ip4")
			}
			val := arg[1:]
			if strings.Contains(val, "/") {
				matched = ipMatchCIDR(c.msg.FromIP, val)
			} else {
				matched = ipMatchAddr(c.msg.FromIP, val)
			}
		case "ip6":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("ip6")
			}
			val := arg[1:]
			if strings.Contains(val, "/") {
				matched = ipMatchCIDR(c.msg.FromIP, val)
			} else {
				matched = ipMatchAddr(c.msg.FromIP, val)
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
				for _, a := range addrs {
					if cidr != "" {
						matched = ipMatchCIDR(c.msg.FromIP, a+cidr)
					} else {
						matched = ipMatchAddr(c.msg.FromIP, a)
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
						if cidr != "" {
							matched = ipMatchCIDR(c.msg.FromIP, a+cidr)
						} else {
							matched = ipMatchAddr(c.msg.FromIP, a)
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
				return "permerror", "", fmt.Errorf("include")
			}
			spec := arg[1:]
			expanded, err := c.expandMacros(spec, domain)
			if err != nil {
				return "permerror", "", err
			}
			sub, _, err := c.evalDomain(expanded, depth+1)
			if err != nil {
				return sub, "", err
			}
			switch sub {
			case "pass":
				matched = true
			case "none":
				return "permerror", "", fmt.Errorf("include none")
			case "permerror", "temperror":
				return sub, "", nil
			default:
				matched = false
			}
		case "exists":
			if !strings.HasPrefix(arg, ":") {
				return "permerror", "", fmt.Errorf("exists")
			}
			spec := arg[1:]
			// NAIVE: write EXPANDED macro into mechanism trace.
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
				mechDesc := "exists:" + expanded // NAIVE: expanded, not original
				c.trace = append(c.trace, string(qual)+mechDesc)
				return qualToResult(qual), string(qual) + mechDesc, nil
			}
		default:
			return "permerror", "", fmt.Errorf("unknown %s", name)
		}
		if matched {
			mechDesc := name
			if arg != "" {
				mechDesc = name + arg
			}
			c.trace = append(c.trace, string(qual)+mechDesc)
			return qualToResult(qual), string(qual) + mechDesc, nil
		}
	}
	// NAIVE: redirect fires on ANY fall-through.
	if redirect != "" {
		expanded, err := c.expandMacros(redirect, domain)
		if err != nil {
			return "permerror", "", err
		}
		sub, _, err := c.evalDomain(expanded, depth+1)
		if err != nil {
			return sub, "", err
		}
		if sub == "none" {
			return "permerror", "", fmt.Errorf("redirect none")
		}
		// NAIVE: writes inner mechanism instead of "redirect=<target>".
		return sub, expanded, nil
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
		ctx := &evalCtx{dns: dns, pol: pol, msg: msg}
		result, mech, _ := ctx.evalDomain(domain, 0)
		v := verdict{
			ID: msg.ID, Result: result, Mechanism: mech, Domain: domain,
			Lookups: ctx.lookups, VoidLookups: ctx.voidLookups, Trace: ctx.trace,
		}
		if v.Trace == nil {
			v.Trace = []string{}
		}
		enc, _ := json.Marshal(v)
		verdictsFile.Write(enc)
		verdictsFile.Write([]byte("\n"))
		counts[result]++
		total++
	}
	if err := scanner.Err(); err != nil && err != io.EOF {
		return err
	}
	keys := []string{"pass", "fail", "softfail", "neutral", "none", "permerror", "temperror"}
	orderedCounts := make(map[string]int)
	for _, k := range keys {
		orderedCounts[k] = counts[k]
	}
	// NAIVE: missing chain_digest.
	summary := struct {
		Total  int            `json:"total"`
		Counts map[string]int `json:"counts"`
	}{Total: total, Counts: orderedCounts}
	sumRaw, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(outDir+"/summary.json", append(sumRaw, '\n'), 0o644); err != nil {
		return err
	}
	return nil
}
GOEOF

cd /app/spf
go build -o /app/spf-trace .
/app/spf-trace
