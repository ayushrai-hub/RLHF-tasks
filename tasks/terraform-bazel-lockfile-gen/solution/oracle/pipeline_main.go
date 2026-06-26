package main

import (
	"encoding/json"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"lockkit/internal/stages"
	"lockkit/internal/types"
)

func main() {
	root := os.Getenv("ENV_ROOT")
	if root == "" {
		root = "/app/environment"
	}
	entry := os.Getenv("ROOT_ENTRY")
	if entry == "" {
		entry = "alpha"
	}
	idxBytes, _ := os.ReadFile(filepath.Join(root, "meta", "roots_index.json"))
	var idx struct {
		Entries map[string]string `json:"entries"`
	}
	_ = json.Unmarshal(idxBytes, &idx)
	rel := idx.Entries[entry]
	rootBytes, _ := os.ReadFile(filepath.Join(root, "fixtures", "roots", rel))
	var roots types.Roots
	_ = json.Unmarshal(rootBytes, &roots)
	roots.EntryID = entry

	catalog := fetchCatalog(os.Getenv("DEPOT_URL"))
	policy := loadPolicy(filepath.Join(root, "docs", "vol_h"), catalog)

	var nodeMap types.NodeMap
	fromCache := false
	if cached, ok := stages.Hydrate(entry, roots); ok {
		nodeMap = cached
		fromCache = true
	} else {
		nodeMap = stages.Resolve(catalog, policy, roots)
		stages.Persist(nodeMap, roots)
	}
	stages.Bump(entry)

	lock, repo, checksum, stub := stages.Emit(nodeMap, policy)
	stages.Finalize(entry, roots, lock, repo, checksum, stub, fromCache)
}

func fetchCatalog(url string) types.Catalog {
	if url == "" {
		url = "http://127.0.0.1:8787/catalog"
	}
	resp, err := http.Get(url)
	if err != nil {
		panic(err)
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	var catalog types.Catalog
	_ = json.Unmarshal(body, &catalog)
	return catalog
}

func loadPolicy(volH string, catalog types.Catalog) types.PolicyCtx {
	var b strings.Builder
	_ = filepath.Walk(volH, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if strings.HasSuffix(path, ".html") || strings.HasSuffix(path, ".txt") {
			data, _ := os.ReadFile(path)
			b.Write(data)
			b.WriteByte('\n')
		}
		return nil
	})
	return types.PolicyCtx{Text: b.String(), Packages: catalog.Packages, Aliases: catalog.Aliases}
}
