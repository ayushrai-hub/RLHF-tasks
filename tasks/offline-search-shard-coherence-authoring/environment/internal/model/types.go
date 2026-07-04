package model

type Plan struct {
	Manifest string `json:"manifest"`
	Queries  string `json:"queries"`
	Cache    string `json:"cache"`
	Limit    int    `json:"limit"`
}

type Manifest struct {
	SnapshotID     string       `json:"snapshot_id"`
	FreshnessEpoch string       `json:"freshness_epoch"`
	Canonical      string       `json:"canonical"`
	Robots         string       `json:"robots"`
	Shards         []ShardEntry `json:"shards"`
}

type ShardEntry struct {
	ID   string `json:"id"`
	Path string `json:"path"`
}

type Query struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

type Document struct {
	URL        string  `json:"url"`
	Title      string  `json:"title"`
	Body       string  `json:"body"`
	AnchorText string  `json:"anchor_text"`
	Published  string  `json:"published"`
	Quality    float64 `json:"quality"`
}

type Result struct {
	Rank           int      `json:"rank,omitempty"`
	CanonicalURL   string   `json:"canonical_url"`
	SelectedURL    string   `json:"selected_url"`
	Title          string   `json:"title"`
	Score          float64  `json:"score"`
	Published      string   `json:"published"`
	SourceShard    string   `json:"source_shard"`
	MatchedTerms   []string `json:"matched_terms"`
	SupportingURLs []string `json:"supporting_urls"`
}

type QueryReport struct {
	ID      string   `json:"id"`
	Text    string   `json:"text"`
	Results []Result `json:"results"`
}

type SegmentTrace struct {
	QueryID        string `json:"query_id"`
	Shard          string `json:"shard"`
	SnapshotHash   string `json:"snapshot_hash"`
	CacheStatus    string `json:"cache_status"`
	CandidateCount int    `json:"candidate_count"`
}

type Provenance struct {
	ManifestPath string         `json:"manifest_path"`
	QueryPath    string         `json:"query_path"`
	CachePath    string         `json:"cache_path"`
	Segments     []SegmentTrace `json:"segments"`
}

type Report struct {
	SchemaVersion string        `json:"schema_version"`
	SnapshotID    string        `json:"snapshot_id"`
	SnapshotHash  string        `json:"snapshot_hash"`
	Limit         int           `json:"limit"`
	Queries       []QueryReport `json:"queries"`
	Provenance    Provenance    `json:"provenance"`
}

type CacheFile struct {
	SchemaVersion string       `json:"schema_version"`
	Entries       []CacheEntry `json:"entries"`
}

type CacheEntry struct {
	SnapshotHash string   `json:"snapshot_hash"`
	QueryID      string   `json:"query_id"`
	QueryText    string   `json:"query_text"`
	Shard        string   `json:"shard"`
	Limit        int      `json:"limit"`
	Results      []Result `json:"results"`
}
