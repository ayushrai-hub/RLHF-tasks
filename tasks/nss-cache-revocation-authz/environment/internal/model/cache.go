package model

type CacheEntry struct {
	Username          string   `json:"username"`
	SubjectID         string   `json:"subject_id"`
	Generation        int      `json:"generation"`
	Groups            []string `json:"groups"`
	DirectoryRevision int      `json:"directory_revision"`
	ProofRevision     int      `json:"proof_revision"`
	ProofAge          int      `json:"proof_age"`
	RefreshedAt       int      `json:"refreshed_at"`
	ExpiresAt         int      `json:"expires_at"`
	RefreshEpoch      int      `json:"refresh_epoch"`
	Revoked           bool     `json:"revoked"`
}

type GroupMember struct {
	Username   string `json:"username"`
	SubjectID  string `json:"subject_id"`
	Generation int    `json:"generation"`
}

type GroupIndexRow struct {
	Group   string        `json:"group"`
	Members []GroupMember `json:"members"`
}
