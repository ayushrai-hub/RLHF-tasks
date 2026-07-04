package search

import (
	"bufio"
	"os"
	"strings"
)

type CanonicalMap map[string]string

type RobotRule struct {
	Prefix string
	Allow  bool
}

func LoadCanonical(path string) (CanonicalMap, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	out := CanonicalMap{}
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) >= 2 {
			out[parts[0]] = parts[1]
		}
	}
	return out, scanner.Err()
}

func (c CanonicalMap) For(raw string) string {
	if v, ok := c[raw]; ok {
		return v
	}
	return raw
}

func LoadRobots(path string) ([]RobotRule, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	var rules []RobotRule
	scanner := bufio.NewScanner(f)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.Split(line, "\t")
		if len(parts) >= 2 {
			rules = append(rules, RobotRule{Prefix: parts[0], Allow: strings.EqualFold(parts[1], "allow")})
		}
	}
	return rules, scanner.Err()
}

// Allowed reports whether a raw URL may contribute to the search result set.
func Allowed(rules []RobotRule, rawURL string) bool {
	for _, r := range rules {
		if strings.HasPrefix(rawURL, r.Prefix) {
			return r.Allow
		}
	}
	return true
}
