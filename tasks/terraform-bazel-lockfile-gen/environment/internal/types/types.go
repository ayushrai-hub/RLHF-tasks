package types

type NodeInfo struct {
	Version string   `json:"version"`
	Deps    []string `json:"deps"`
}

type NodeMap struct {
	EntryID      string              `json:"entry_id"`
	StorageClass string              `json:"storage_class"`
	Nodes        map[string]NodeInfo `json:"nodes"`
}

type LockRow struct {
	ModuleID string `json:"module_id"`
	RepoKey  string `json:"repo_key"`
	Version  string `json:"version"`
}

type LockSnapshot struct {
	EntryID string    `json:"entry_id"`
	Rows    []LockRow `json:"rows"`
}

type RepoRow struct {
	ModuleID string `json:"module_id"`
	RepoKey  string `json:"repo_key"`
	URL      string `json:"url"`
}

type ChecksumRow struct {
	RepoKey string `json:"repo_key"`
	Digest  string `json:"digest"`
}

type Package struct {
	Latest   string              `json:"latest"`
	Versions []string            `json:"versions"`
	Deps     map[string][]string `json:"deps"`
	Repo     string              `json:"repo"`
	Checksum string              `json:"checksum"`
}

type Catalog struct {
	Packages map[string]Package `json:"packages"`
	Aliases  map[string]string  `json:"aliases"`
}

type PolicyCtx struct {
	Text     string
	Packages map[string]Package
	Aliases  map[string]string
}

type Roots struct {
	EntryID      string   `json:"entry_id"`
	StorageClass string   `json:"storage_class"`
	Seeds        []string `json:"seeds"`
}

type ClosureSlot struct {
	SeedDigest  string              `json:"seed_digest"`
	Nodes       map[string]NodeInfo `json:"nodes"`
	Pins        map[string]string   `json:"pins"`
	LinkDigest  string              `json:"link_digest"`
	SealedAtGen int                 `json:"sealed_at_gen"`
}

type SlotsLedger struct {
	Slots map[string]ClosureSlot `json:"slots"`
}

type ReplayGen struct {
	Gen int `json:"gen"`
}

type ModuleLockStub struct {
	EntryID    string   `json:"entry_id"`
	Lines      []string `json:"lines"`
	StubRollup string `json:"stub_rollup"`
}

type ChainRecord struct {
	EntryID     string `json:"entry_id"`
	Gen         int    `json:"gen"`
	LinkDigest  string `json:"link_digest"`
	ChainPrefix string `json:"chain_prefix"`
}
