#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/go/bin:${PATH:-}"
cd /app/environment

cat > internal/fsutil/hash.go <<'GO'
package fsutil

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/model"
)

func SnapshotHash(manifestPath string, m model.Manifest) (string, error) {
	dir := filepath.Dir(manifestPath)
	h := sha256.New()
	add := func(rel string) error {
		path := RelTo(dir, rel)
		b, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		h.Write([]byte(filepath.Clean(rel)))
		h.Write([]byte("\n"))
		h.Write(b)
		h.Write([]byte("\n"))
		return nil
	}
	if err := add(filepath.Base(manifestPath)); err != nil {
		return "", err
	}
	if err := add(m.Canonical); err != nil {
		return "", err
	}
	if err := add(m.Robots); err != nil {
		return "", err
	}
	for _, shard := range m.Shards {
		if err := add(shard.Path); err != nil {
			return "", err
		}
	}
	return fmt.Sprintf("sha256:%s", hex.EncodeToString(h.Sum(nil))), nil
}
GO

cat > internal/search/query.go <<'GO'
package search

import (
	"strings"
	"unicode"
)

type QuerySpec struct {
	Terms   []string
	Phrases []string
}

func ParseQuery(text string) QuerySpec {
	lower := strings.ToLower(text)
	phrases := []string{}
	inQuote := false
	var phrase strings.Builder
	for _, r := range lower {
		if r == '"' {
			if inQuote {
				parts := tokens(phrase.String())
				if len(parts) > 0 {
					phrases = append(phrases, strings.Join(parts, " "))
				}
				phrase.Reset()
			}
			inQuote = !inQuote
			continue
		}
		if inQuote {
			phrase.WriteRune(r)
		}
	}
	seen := map[string]bool{}
	terms := []string{}
	for _, term := range tokens(lower) {
		if term == "" || seen[term] {
			continue
		}
		seen[term] = true
		terms = append(terms, term)
	}
	return QuerySpec{Terms: terms, Phrases: phrases}
}

func tokens(text string) []string {
	lower := strings.ToLower(text)
	return strings.FieldsFunc(lower, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	})
}

func countTerm(xs []string, term string) int {
	n := 0
	for _, x := range xs {
		if x == term {
			n++
		}
	}
	return n
}

func countPhrase(text, phrase string) int {
	hayTokens := tokens(text)
	needleTokens := tokens(phrase)
	if len(needleTokens) == 0 || len(needleTokens) > len(hayTokens) {
		return 0
	}
	count := 0
	for i := 0; i+len(needleTokens) <= len(hayTokens); i++ {
		ok := true
		for j, tok := range needleTokens {
			if hayTokens[i+j] != tok {
				ok = false
				break
			}
		}
		if ok {
			count++
		}
	}
	return count
}
GO

cat > internal/search/rules.go <<'GO'
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

func Allowed(rules []RobotRule, rawURL string) bool {
	bestLen := -1
	allow := true
	for _, r := range rules {
		if strings.HasPrefix(rawURL, r.Prefix) && len(r.Prefix) > bestLen {
			bestLen = len(r.Prefix)
			allow = r.Allow
		}
	}
	return allow
}
GO

cat > internal/search/segment.go <<'GO'
package search

import (
	"offline-search-shard-coherence/internal/fsutil"
	"offline-search-shard-coherence/internal/model"
)

func SearchShard(path, shardID string, query model.Query, canon CanonicalMap, robots []RobotRule, epoch string) ([]model.Result, error) {
	docs, err := fsutil.ReadJSONL[model.Document](path)
	if err != nil {
		return nil, err
	}
	spec := ParseQuery(query.Text)
	out := []model.Result{}
	for _, doc := range docs {
		if !Allowed(robots, doc.URL) {
			continue
		}
		canonicalURL := canon.For(doc.URL)
		score, matched, err := ScoreDocument(doc, spec, epoch)
		if err != nil {
			return nil, err
		}
		if len(matched) == 0 {
			continue
		}
		out = append(out, model.Result{
			CanonicalURL:   canonicalURL,
			SelectedURL:    doc.URL,
			Title:          doc.Title,
			Score:          score,
			Published:      doc.Published,
			SourceShard:    shardID,
			MatchedTerms:   matched,
			SupportingURLs: []string{doc.URL},
		})
	}
	return out, nil
}
GO

cat > internal/search/merge.go <<'GO'
package search

import (
	"sort"

	"offline-search-shard-coherence/internal/model"
)

func MergeResults(candidates []model.Result, limit int) []model.Result {
	groups := map[string][]model.Result{}
	for _, r := range candidates {
		groups[r.CanonicalURL] = append(groups[r.CanonicalURL], r)
	}
	merged := make([]model.Result, 0, len(groups))
	for _, group := range groups {
		sort.Slice(group, func(i, j int) bool { return betterWithinCanonical(group[i], group[j]) })
		best := group[0]
		seen := map[string]bool{}
		urls := make([]string, 0, len(group))
		for _, r := range group {
			if !seen[r.SelectedURL] {
				seen[r.SelectedURL] = true
				urls = append(urls, r.SelectedURL)
			}
		}
		sort.Strings(urls)
		best.SupportingURLs = urls
		merged = append(merged, best)
	}
	sort.Slice(merged, func(i, j int) bool { return better(merged[i], merged[j]) })
	if limit > 0 && len(merged) > limit {
		merged = merged[:limit]
	}
	for i := range merged {
		merged[i].Rank = i + 1
	}
	return merged
}

func betterWithinCanonical(a, b model.Result) bool {
	if a.Score != b.Score {
		return a.Score > b.Score
	}
	if a.Published != b.Published {
		return a.Published > b.Published
	}
	return a.SelectedURL < b.SelectedURL
}

func better(a, b model.Result) bool {
	if a.Score != b.Score {
		return a.Score > b.Score
	}
	if a.Published != b.Published {
		return a.Published > b.Published
	}
	return a.CanonicalURL < b.CanonicalURL
}
GO

cat > internal/search/cache.go <<'GO'
package search

import (
	"encoding/json"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/model"
)

func LoadCache(path string) (model.CacheFile, error) {
	b, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return model.CacheFile{SchemaVersion: "segment-cache-v1"}, nil
	}
	if err != nil {
		return model.CacheFile{}, err
	}
	var cache model.CacheFile
	if err := json.Unmarshal(b, &cache); err != nil {
		return model.CacheFile{}, err
	}
	if cache.SchemaVersion == "" {
		cache.SchemaVersion = "segment-cache-v1"
	}
	return cache, nil
}

func Lookup(cache model.CacheFile, snapshotHash string, query model.Query, shard string, limit int) ([]model.Result, string) {
	sawRelated := false
	for _, e := range cache.Entries {
		if e.QueryID == query.ID && e.Shard == shard {
			sawRelated = true
			if e.SnapshotHash == snapshotHash && e.QueryText == query.Text && e.Limit == limit {
				return cloneResults(e.Results), "hit"
			}
		}
	}
	if sawRelated {
		return nil, "stale"
	}
	return nil, "miss"
}

func WriteCache(path string, entries []model.CacheEntry) error {
	cache := model.CacheFile{SchemaVersion: "segment-cache-v1", Entries: entries}
	b, err := json.MarshalIndent(cache, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0o644)
}

func cloneResults(in []model.Result) []model.Result {
	out := make([]model.Result, len(in))
	copy(out, in)
	return out
}
GO

gofmt -w internal/fsutil/hash.go internal/search/query.go internal/search/rules.go internal/search/segment.go internal/search/merge.go internal/search/cache.go
go test ./...
/app/environment/scripts/check_public.sh
