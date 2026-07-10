#!/usr/bin/env bash
set -euo pipefail

cat > /app/task_file/main.go <<'GO'
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

type Policy struct {
	PublicSuffixes       []string `json:"public_suffixes"`
	SensitivePatterns    []string `json:"sensitive_name_patterns"`
	MaxCookieHeaderBytes int      `json:"max_cookie_header_bytes"`
}

type Event struct {
	Type                 string   `json:"type"`
	ID                   string   `json:"id"`
	URL                  string   `json:"url"`
	SetCookie            []string `json:"set_cookie"`
	Method               string   `json:"method"`
	TopLevelSite         string   `json:"top_level_site"`
	IsTopLevelNavigation bool     `json:"is_top_level_navigation"`
}

type Cookie struct {
	Name     string
	Value    string
	Domain   string
	Path     string
	HostOnly bool
	Secure   bool
	HttpOnly bool
	SameSite string
}

type Rejection struct {
	EventID string `json:"event_id"`
	Name    string `json:"name"`
	Reason  string `json:"reason"`
}

type BlockedCookie struct {
	Name   string `json:"name"`
	Reason string `json:"reason"`
}

type BlockedCookieKey struct {
	Name   string `json:"name"`
	Domain string `json:"domain"`
	Path   string `json:"path"`
	Reason string `json:"reason"`
}

type SentCookieKey struct {
	Name   string `json:"name"`
	Domain string `json:"domain"`
	Path   string `json:"path"`
}

type ResponseReport struct {
	ID                 string          `json:"id"`
	AcceptedCookieKeys []SentCookieKey `json:"accepted_cookie_keys"`
	DeletedCookieKeys  []SentCookieKey `json:"deleted_cookie_keys"`
}

type SetCookieAudit struct {
	EventID      string `json:"event_id"`
	Index        int    `json:"index"`
	Name         string `json:"name"`
	Domain       string `json:"domain"`
	Path         string `json:"path"`
	HostOnly     bool   `json:"host_only"`
	Secure       bool   `json:"secure"`
	HttpOnly     bool   `json:"http_only"`
	SameSite     string `json:"same_site"`
	MaxAgeState  string `json:"max_age_state"`
	Disposition  string `json:"disposition"`
	Reason       string `json:"reason"`
}

type RequestReport struct {
	ID             string          `json:"id"`
	SentCookies    []string        `json:"sent_cookies"`
	SentCookieKeys []SentCookieKey `json:"sent_cookie_keys"`
	BlockedCookies []BlockedCookie `json:"blocked_cookies"`
	BlockedKeys    []BlockedCookieKey `json:"blocked_cookie_keys"`
	CookieHeader   string          `json:"cookie_header"`
	HeaderBytes    int             `json:"header_bytes"`
}

type StoredCookie struct {
	Name     string   `json:"name"`
	Domain   string   `json:"domain"`
	Path     string   `json:"path"`
	HostOnly bool     `json:"host_only"`
	Secure   bool     `json:"secure"`
	HttpOnly bool     `json:"http_only"`
	SameSite string   `json:"same_site"`
	Risks    []string `json:"risks"`
}

type DomainDiagnostic struct {
	Domain                string         `json:"domain"`
	StoredCookieCount     int            `json:"stored_cookie_count"`
	HostOnlyCookieCount   int            `json:"host_only_cookie_count"`
	SecureCookieCount     int            `json:"secure_cookie_count"`
	SentCount             int            `json:"sent_count"`
	BlockedCount          int            `json:"blocked_count"`
	RiskCounts            map[string]int `json:"risk_counts"`
}

type RequestDiagnostic struct {
	ID                      string          `json:"id"`
	RegistrableSite        string          `json:"registrable_site"`
	TopLevelSite           string          `json:"top_level_site"`
	SameSiteContext         bool            `json:"same_site_context"`
	EligibleCookieKeys     []SentCookieKey `json:"eligible_cookie_keys"`
	SentCookieKeys         []SentCookieKey `json:"sent_cookie_keys"`
	BlockedReasonCounts    map[string]int  `json:"blocked_reason_counts"`
	HeaderLimitBytesSkipped int             `json:"header_limit_bytes_skipped"`
}

type LifecycleRow struct {
	Name          string `json:"name"`
	Domain        string `json:"domain"`
	Path          string `json:"path"`
	AcceptedCount int    `json:"accepted_count"`
	ReplacedCount int    `json:"replaced_count"`
	DeletedCount  int    `json:"deleted_count"`
	SentCount     int    `json:"sent_count"`
	BlockedCount  int    `json:"blocked_count"`
	FirstEventID  string `json:"first_event_id"`
	LastEventID   string `json:"last_event_id"`
	FinalState    string `json:"final_state"`
}

type JarSnapshot struct {
	ID                string          `json:"id"`
	StoredCount       int             `json:"stored_count"`
	HostOnlyCount     int             `json:"host_only_count"`
	DomainCookieCount int             `json:"domain_cookie_count"`
	SecureCount       int             `json:"secure_count"`
	JarCookieKeys     []SentCookieKey `json:"jar_cookie_keys"`
	RiskCounts        map[string]int  `json:"risk_counts"`
}

type Summary struct {
	Accepted          int            `json:"accepted"`
	SetCookieRejected int            `json:"set_cookie_rejected"`
	Deleted           int            `json:"deleted"`
	RequestCount      int            `json:"request_count"`
	RiskCounts        map[string]int `json:"risk_counts"`
	TruncatedRequests int            `json:"truncated_requests"`
}

type Report struct {
	Summary           Summary            `json:"summary"`
	Responses         []ResponseReport   `json:"responses"`
	SetCookieAudit    []SetCookieAudit   `json:"set_cookie_audit"`
	Requests          []RequestReport    `json:"requests"`
	Rejections        []Rejection        `json:"rejections"`
	DomainDiagnostics []DomainDiagnostic `json:"domain_diagnostics"`
	RequestDiagnostics []RequestDiagnostic `json:"request_diagnostics"`
	CookieLifecycle    []LifecycleRow      `json:"cookie_lifecycle"`
	JarSnapshots       []JarSnapshot       `json:"jar_snapshots"`
	StoredCookies     []StoredCookie     `json:"stored_cookies"`
}

func readPolicy(path string) (Policy, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Policy{}, err
	}
	var p Policy
	err = json.Unmarshal(data, &p)
	return p, err
}

func readEvents(path string) ([]Event, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()
	var events []Event
	scanner := bufio.NewScanner(file)
	scanner.Buffer(make([]byte, 1024), 16*1024*1024)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		var ev Event
		if err := json.Unmarshal([]byte(line), &ev); err != nil {
			return nil, err
		}
		events = append(events, ev)
	}
	return events, scanner.Err()
}

func parsed(raw string) *url.URL {
	u, _ := url.Parse(raw)
	return u
}

func host(raw string) string {
	return strings.ToLower(parsed(raw).Hostname())
}

func scheme(raw string) string {
	return strings.ToLower(parsed(raw).Scheme)
}

func pathOf(raw string) string {
	p := parsed(raw).EscapedPath()
	if p == "" {
		return "/"
	}
	return p
}

func defaultPath(raw string) string {
	p := pathOf(raw)
	if !strings.HasPrefix(p, "/") {
		return "/"
	}
	idx := strings.LastIndex(p, "/")
	if idx <= 0 {
		return "/"
	}
	return p[:idx]
}

func domainMatch(reqHost, cookieDomain string) bool {
	reqHost = strings.ToLower(reqHost)
	cookieDomain = strings.ToLower(cookieDomain)
	return reqHost == cookieDomain || strings.HasSuffix(reqHost, "."+cookieDomain)
}

func pathMatch(reqPath, cookiePath string) bool {
	if reqPath == cookiePath {
		return true
	}
	if !strings.HasPrefix(reqPath, cookiePath) {
		return false
	}
	return strings.HasSuffix(cookiePath, "/") || strings.HasPrefix(reqPath[len(cookiePath):], "/")
}

func publicSuffix(domain string, suffixes []string) bool {
	d := strings.Trim(strings.ToLower(domain), ".")
	for _, suffix := range suffixes {
		if d == strings.ToLower(suffix) {
			return true
		}
	}
	return false
}

func registrableSite(rawHost string, suffixes []string) string {
	h := strings.Trim(strings.ToLower(rawHost), ".")
	labels := strings.Split(h, ".")
	best := ""
	for _, suffix := range suffixes {
		s := strings.ToLower(suffix)
		if h == s || strings.HasSuffix(h, "."+s) {
			if best == "" || len(strings.Split(s, ".")) > len(strings.Split(best, ".")) {
				best = s
			}
		}
	}
	if best == "" {
		if len(labels) >= 2 {
			return strings.Join(labels[len(labels)-2:], ".")
		}
		return h
	}
	suffixLabels := strings.Split(best, ".")
	if len(labels) <= len(suffixLabels) {
		return h
	}
	return strings.Join(labels[len(labels)-len(suffixLabels)-1:], ".")
}

func parseSetCookie(header string) (string, string, map[string]string, map[string]bool) {
	parts := strings.Split(header, ";")
	attrs := map[string]string{}
	flags := map[string]bool{}
	if len(parts) == 0 || !strings.Contains(parts[0], "=") {
		return "", "", attrs, flags
	}
	first := strings.SplitN(parts[0], "=", 2)
	name := strings.TrimSpace(first[0])
	value := strings.TrimSpace(first[1])
	for _, raw := range parts[1:] {
		attr := strings.TrimSpace(raw)
		if attr == "" {
			continue
		}
		if strings.Contains(attr, "=") {
			pair := strings.SplitN(attr, "=", 2)
			attrs[strings.ToLower(strings.TrimSpace(pair[0]))] = strings.TrimSpace(pair[1])
		} else {
			flags[strings.ToLower(attr)] = true
		}
	}
	return name, value, attrs, flags
}

func sameSiteValue(attrs map[string]string) string {
	value := "Lax"
	if raw, ok := attrs["samesite"]; ok {
		value = strings.ToLower(raw)
		switch value {
		case "strict":
			return "Strict"
		case "lax":
			return "Lax"
		case "none":
			return "None"
		default:
			return "Lax"
		}
	}
	return value
}

func maxAgeState(attrs map[string]string) string {
	raw, ok := attrs["max-age"]
	if !ok {
		return "absent"
	}
	value, err := strconv.Atoi(strings.TrimSpace(raw))
	if err != nil {
		return "invalid"
	}
	if value <= 0 {
		return "delete"
	}
	return "positive"
}

func reject(rejections *[]Rejection, rejected *int, eventID, name, reason string) {
	(*rejected)++
	*rejections = append(*rejections, Rejection{EventID: eventID, Name: name, Reason: reason})
}

func risks(cookie Cookie, patterns []*regexp.Regexp) []string {
	out := []string{}
	if !cookie.HostOnly {
		out = append(out, "overbroad_domain")
	}
	if !cookie.Secure {
		out = append(out, "missing_secure")
	}
	lower := strings.ToLower(cookie.Name)
	for _, pattern := range patterns {
		if pattern.MatchString(lower) {
			if !cookie.HttpOnly {
				out = append(out, "missing_httponly")
			}
			break
		}
	}
	return out
}

func removeMatching(jar []Cookie, name, domain, path string) ([]Cookie, bool) {
	out := jar[:0]
	removed := false
	for _, cookie := range jar {
		if cookie.Name == name && cookie.Domain == domain && cookie.Path == path {
			removed = true
			continue
		}
		out = append(out, cookie)
	}
	return out, removed
}

type lifeKey struct {
	Name   string
	Domain string
	Path   string
}

func asCookieKey(cookie Cookie) SentCookieKey {
	return SentCookieKey{Name: cookie.Name, Domain: cookie.Domain, Path: cookie.Path}
}

func makeJarSnapshot(eventID string, jar []Cookie, patterns []*regexp.Regexp) JarSnapshot {
	keys := make([]SentCookieKey, 0, len(jar))
	riskCounts := map[string]int{}
	hostOnlyCount, domainCookieCount, secureCount := 0, 0, 0
	for _, cookie := range jar {
		keys = append(keys, asCookieKey(cookie))
		if cookie.HostOnly {
			hostOnlyCount++
		} else {
			domainCookieCount++
		}
		if cookie.Secure {
			secureCount++
		}
		for _, risk := range risks(cookie, patterns) {
			riskCounts[risk]++
		}
	}
	return JarSnapshot{
		ID:                eventID,
		StoredCount:       len(jar),
		HostOnlyCount:     hostOnlyCount,
		DomainCookieCount: domainCookieCount,
		SecureCount:       secureCount,
		JarCookieKeys:     keys,
		RiskCounts:        riskCounts,
	}
}

func run(policyPath, eventsPath, outputPath string) error {
	policy, err := readPolicy(policyPath)
	if err != nil {
		return err
	}
	events, err := readEvents(eventsPath)
	if err != nil {
		return err
	}
	var patterns []*regexp.Regexp
	for _, raw := range policy.SensitivePatterns {
		patterns = append(patterns, regexp.MustCompile("(?i)"+raw))
	}
	jar := []Cookie{}
	rejections := []Rejection{}
	responses := []ResponseReport{}
	setCookieAudit := []SetCookieAudit{}
	requests := []RequestReport{}
	requestDiagnostics := []RequestDiagnostic{}
	jarSnapshots := []JarSnapshot{}
	accepted, rejected, deleted, truncatedRequests := 0, 0, 0, 0
	domainSent := map[string]int{}
	domainBlocked := map[string]int{}
	lifecycle := map[lifeKey]*LifecycleRow{}
	touchLifecycle := func(name, domain, path, eventID string) *LifecycleRow {
		key := lifeKey{Name: name, Domain: domain, Path: path}
		row := lifecycle[key]
		if row == nil {
			row = &LifecycleRow{
				Name:         name,
				Domain:       domain,
				Path:         path,
				FirstEventID: eventID,
				LastEventID:  eventID,
				FinalState:   "absent",
			}
			lifecycle[key] = row
		} else {
			row.LastEventID = eventID
		}
		return row
	}

	for _, ev := range events {
		if ev.Type == "response" {
			origin := host(ev.URL)
			acceptedKeys := []SentCookieKey{}
			deletedKeys := []SentCookieKey{}
			for headerIndex, header := range ev.SetCookie {
				name, value, attrs, flags := parseSetCookie(header)
				if name == "" {
					setCookieAudit = append(setCookieAudit, SetCookieAudit{
						EventID:     ev.ID,
						Index:       headerIndex,
						Name:        "",
						Domain:      "",
						Path:        "",
						HostOnly:    false,
						Secure:      false,
						HttpOnly:    false,
						SameSite:    "Lax",
						MaxAgeState: "absent",
						Disposition: "rejected",
						Reason:      "empty_name",
					})
					reject(&rejections, &rejected, ev.ID, name, "empty_name")
					continue
				}
				audit := SetCookieAudit{
					EventID:     ev.ID,
					Index:       headerIndex,
					Name:        name,
					HostOnly:    true,
					Secure:      flags["secure"],
					HttpOnly:    flags["httponly"],
					SameSite:    sameSiteValue(attrs),
					MaxAgeState: maxAgeState(attrs),
				}
				hostOnly := true
				cookieDomain := origin
				if dom, ok := attrs["domain"]; ok {
					hostOnly = false
					cookieDomain = strings.Trim(strings.ToLower(dom), ".")
					if publicSuffix(cookieDomain, policy.PublicSuffixes) {
						audit.Domain = cookieDomain
						audit.Path = defaultPath(ev.URL)
						if p, ok := attrs["path"]; ok {
							audit.Path = p
						}
						audit.HostOnly = false
						audit.Disposition = "rejected"
						audit.Reason = "public_suffix_domain"
						setCookieAudit = append(setCookieAudit, audit)
						reject(&rejections, &rejected, ev.ID, name, "public_suffix_domain")
						continue
					}
					if !domainMatch(origin, cookieDomain) {
						audit.Domain = cookieDomain
						audit.Path = defaultPath(ev.URL)
						if p, ok := attrs["path"]; ok {
							audit.Path = p
						}
						audit.HostOnly = false
						audit.Disposition = "rejected"
						audit.Reason = "domain_not_suffix"
						setCookieAudit = append(setCookieAudit, audit)
						reject(&rejections, &rejected, ev.ID, name, "domain_not_suffix")
						continue
					}
				}
				cookiePath := defaultPath(ev.URL)
				if p, ok := attrs["path"]; ok {
					cookiePath = p
				}
				secure := flags["secure"]
				httpOnly := flags["httponly"]
				sameSite := sameSiteValue(attrs)
				audit.Domain = cookieDomain
				audit.Path = cookiePath
				audit.HostOnly = hostOnly
				audit.Secure = secure
				audit.HttpOnly = httpOnly
				audit.SameSite = sameSite
				if sameSite == "None" && !secure {
					audit.Disposition = "rejected"
					audit.Reason = "samesite_none_without_secure"
					setCookieAudit = append(setCookieAudit, audit)
					reject(&rejections, &rejected, ev.ID, name, "samesite_none_without_secure")
					continue
				}
				if strings.HasPrefix(name, "__Secure-") && !secure {
					audit.Disposition = "rejected"
					audit.Reason = "secure_prefix_without_secure"
					setCookieAudit = append(setCookieAudit, audit)
					reject(&rejections, &rejected, ev.ID, name, "secure_prefix_without_secure")
					continue
				}
				if strings.HasPrefix(name, "__Host-") && (!secure || !hostOnly || cookiePath != "/") {
					audit.Disposition = "rejected"
					audit.Reason = "host_prefix_invalid"
					setCookieAudit = append(setCookieAudit, audit)
					reject(&rejections, &rejected, ev.ID, name, "host_prefix_invalid")
					continue
				}
				if rawMaxAge, ok := attrs["max-age"]; ok {
					if maxAge, err := strconv.Atoi(strings.TrimSpace(rawMaxAge)); err == nil && maxAge <= 0 {
						var removed bool
						jar, removed = removeMatching(jar, name, cookieDomain, cookiePath)
						if removed {
							deleted++
							deletedKeys = append(deletedKeys, SentCookieKey{Name: name, Domain: cookieDomain, Path: cookiePath})
							touchLifecycle(name, cookieDomain, cookiePath, ev.ID).DeletedCount++
							audit.Disposition = "deleted"
						} else {
							audit.Disposition = "ignored_delete"
						}
						setCookieAudit = append(setCookieAudit, audit)
						continue
					}
				}
				var replaced bool
				jar, replaced = removeMatching(jar, name, cookieDomain, cookiePath)
				life := touchLifecycle(name, cookieDomain, cookiePath, ev.ID)
				if replaced {
					life.ReplacedCount++
				}
				life.AcceptedCount++
				jar = append(jar, Cookie{Name: name, Value: value, Domain: cookieDomain, Path: cookiePath, HostOnly: hostOnly, Secure: secure, HttpOnly: httpOnly, SameSite: sameSite})
				acceptedKeys = append(acceptedKeys, SentCookieKey{Name: name, Domain: cookieDomain, Path: cookiePath})
				accepted++
				audit.Disposition = "accepted"
				setCookieAudit = append(setCookieAudit, audit)
			}
			responses = append(responses, ResponseReport{ID: ev.ID, AcceptedCookieKeys: acceptedKeys, DeletedCookieKeys: deletedKeys})
			jarSnapshots = append(jarSnapshots, makeJarSnapshot(ev.ID, jar, patterns))
		} else if ev.Type == "request" {
			reqHost := host(ev.URL)
			reqPath := pathOf(ev.URL)
			reqSite := registrableSite(reqHost, policy.PublicSuffixes)
			topSite := strings.ToLower(ev.TopLevelSite)
			sameSiteReq := reqSite == topSite
			sent := []string{}
			sentKeys := []SentCookieKey{}
			headerPairs := []string{}
			blocked := []BlockedCookie{}
			blockedKeys := []BlockedCookieKey{}
			eligibleKeys := []SentCookieKey{}
			blockedReasonCounts := map[string]int{}
			headerLimitBytesSkipped := 0
			headerBytes := 0
			truncated := false
			for _, cookie := range jar {
				reason := ""
				if cookie.HostOnly && cookie.Domain != reqHost {
					reason = "domain_mismatch"
				} else if !cookie.HostOnly && !domainMatch(reqHost, cookie.Domain) {
					reason = "domain_mismatch"
				} else if !pathMatch(reqPath, cookie.Path) {
					reason = "path_mismatch"
				} else if cookie.Secure && scheme(ev.URL) != "https" {
					reason = "secure_only"
				} else if cookie.SameSite == "Strict" && !sameSiteReq {
					reason = "samesite_strict"
				} else if cookie.SameSite == "Lax" && !(sameSiteReq || (ev.IsTopLevelNavigation && strings.ToUpper(ev.Method) == "GET")) {
					reason = "samesite_lax"
				}
				if reason == "" {
					eligibleKeys = append(eligibleKeys, asCookieKey(cookie))
					pair := cookie.Name + "=" + cookie.Value
					nextLen := len(pair)
					if len(sent) > 0 {
						nextLen = headerBytes + 2 + len(pair)
					}
					if nextLen > policy.MaxCookieHeaderBytes {
						reason = "header_limit"
						truncated = true
						headerLimitBytesSkipped += len(pair)
					} else {
						sent = append(sent, cookie.Name)
						sentKeys = append(sentKeys, asCookieKey(cookie))
						headerPairs = append(headerPairs, pair)
						headerBytes = nextLen
						domainSent[cookie.Domain]++
						touchLifecycle(cookie.Name, cookie.Domain, cookie.Path, ev.ID).SentCount++
					}
				}
				if reason != "" {
					blocked = append(blocked, BlockedCookie{Name: cookie.Name, Reason: reason})
					blockedKeys = append(blockedKeys, BlockedCookieKey{Name: cookie.Name, Domain: cookie.Domain, Path: cookie.Path, Reason: reason})
					domainBlocked[cookie.Domain]++
					blockedReasonCounts[reason]++
					touchLifecycle(cookie.Name, cookie.Domain, cookie.Path, ev.ID).BlockedCount++
				}
			}
			if truncated {
				truncatedRequests++
			}
			requests = append(requests, RequestReport{ID: ev.ID, SentCookies: sent, SentCookieKeys: sentKeys, BlockedCookies: blocked, BlockedKeys: blockedKeys, CookieHeader: strings.Join(headerPairs, "; "), HeaderBytes: headerBytes})
			requestDiagnostics = append(requestDiagnostics, RequestDiagnostic{
				ID:                       ev.ID,
				RegistrableSite:         reqSite,
				TopLevelSite:            topSite,
				SameSiteContext:          sameSiteReq,
				EligibleCookieKeys:      eligibleKeys,
				SentCookieKeys:          sentKeys,
				BlockedReasonCounts:     blockedReasonCounts,
				HeaderLimitBytesSkipped: headerLimitBytesSkipped,
			})
		}
	}

	stored := []StoredCookie{}
	riskCounts := map[string]int{}
	type domainStat struct {
		Stored   int
		HostOnly int
		Secure   int
		Risks    map[string]int
	}
	domainStats := map[string]*domainStat{}
	for _, cookie := range jar {
		rs := risks(cookie, patterns)
		for _, risk := range rs {
			riskCounts[risk]++
		}
		stat := domainStats[cookie.Domain]
		if stat == nil {
			stat = &domainStat{Risks: map[string]int{}}
			domainStats[cookie.Domain] = stat
		}
		stat.Stored++
		if cookie.HostOnly {
			stat.HostOnly++
		}
		if cookie.Secure {
			stat.Secure++
		}
		for _, risk := range rs {
			stat.Risks[risk]++
		}
		stored = append(stored, StoredCookie{Name: cookie.Name, Domain: cookie.Domain, Path: cookie.Path, HostOnly: cookie.HostOnly, Secure: cookie.Secure, HttpOnly: cookie.HttpOnly, SameSite: cookie.SameSite, Risks: rs})
	}
	finalKeys := map[lifeKey]bool{}
	for _, cookie := range jar {
		finalKeys[lifeKey{Name: cookie.Name, Domain: cookie.Domain, Path: cookie.Path}] = true
	}
	lifecycleRows := make([]LifecycleRow, 0, len(lifecycle))
	for key, row := range lifecycle {
		if finalKeys[key] {
			row.FinalState = "stored"
		} else {
			row.FinalState = "absent"
		}
		lifecycleRows = append(lifecycleRows, *row)
	}
	sort.Slice(lifecycleRows, func(i, j int) bool {
		if lifecycleRows[i].Domain != lifecycleRows[j].Domain {
			return lifecycleRows[i].Domain < lifecycleRows[j].Domain
		}
		if lifecycleRows[i].Path != lifecycleRows[j].Path {
			return lifecycleRows[i].Path < lifecycleRows[j].Path
		}
		return lifecycleRows[i].Name < lifecycleRows[j].Name
	})
	for _, key := range []string{"missing_httponly", "missing_secure", "overbroad_domain"} {
		if riskCounts[key] == 0 {
			delete(riskCounts, key)
		}
	}
	domainSet := map[string]bool{}
	for domain := range domainStats {
		domainSet[domain] = true
	}
	for domain := range domainSent {
		domainSet[domain] = true
	}
	for domain := range domainBlocked {
		domainSet[domain] = true
	}
	domains := make([]string, 0, len(domainSet))
	for domain := range domainSet {
		domains = append(domains, domain)
	}
	sort.Strings(domains)
	diagnostics := make([]DomainDiagnostic, 0, len(domains))
	for _, domain := range domains {
		stat := domainStats[domain]
		riskMap := map[string]int{}
		storedCount, hostOnlyCount, secureCount := 0, 0, 0
		if stat != nil {
			storedCount = stat.Stored
			hostOnlyCount = stat.HostOnly
			secureCount = stat.Secure
			for risk, count := range stat.Risks {
				if count != 0 {
					riskMap[risk] = count
				}
			}
		}
		diagnostics = append(diagnostics, DomainDiagnostic{
			Domain:              domain,
			StoredCookieCount:   storedCount,
			HostOnlyCookieCount: hostOnlyCount,
			SecureCookieCount:   secureCount,
			SentCount:           domainSent[domain],
			BlockedCount:        domainBlocked[domain],
			RiskCounts:          riskMap,
		})
	}
	report := Report{
		Summary: Summary{Accepted: accepted, SetCookieRejected: rejected, Deleted: deleted, RequestCount: len(requests), RiskCounts: riskCounts, TruncatedRequests: truncatedRequests},
		Responses: responses, SetCookieAudit: setCookieAudit, Requests: requests, Rejections: rejections, DomainDiagnostics: diagnostics, RequestDiagnostics: requestDiagnostics, CookieLifecycle: lifecycleRows, JarSnapshots: jarSnapshots, StoredCookies: stored,
	}
	if err := os.MkdirAll(filepath.Dir(outputPath), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(outputPath, data, 0o644)
}

func main() {
	policy := flag.String("policy", "", "policy JSON path")
	events := flag.String("events", "", "events JSONL path")
	output := flag.String("output", "", "report JSON path")
	flag.Parse()
	if *policy == "" || *events == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "usage: cookie-auditor --policy policy.json --events events.jsonl --output report.json")
		os.Exit(2)
	}
	if err := run(*policy, *events, *output); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
GO

if command -v gofmt >/dev/null 2>&1; then
	gofmt -w /app/task_file/main.go
fi
