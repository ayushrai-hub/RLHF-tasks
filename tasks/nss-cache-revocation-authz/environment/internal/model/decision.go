package model

type DecisionRecord struct {
	Step              int      `json:"step"`
	Tick              int      `json:"tick"`
	Username          string   `json:"username"`
	SubjectID         string   `json:"subject_id"`
	Resource          string   `json:"resource"`
	Action            string   `json:"action"`
	Result            string   `json:"result"`
	Reason            string   `json:"reason"`
	RequiredGroups    []string `json:"required_groups"`
	Groups            []string `json:"groups"`
	DirectoryRevision int      `json:"directory_revision"`
	CacheRevision     int      `json:"cache_revision"`
	ProofRevision     int      `json:"proof_revision"`
	ProofAge          int      `json:"proof_age"`
	Generation        int      `json:"generation"`
}

type RefreshRecord struct {
	Step          int    `json:"step"`
	Tick          int    `json:"tick"`
	Revision      int    `json:"revision"`
	ProofRevision int    `json:"proof_revision"`
	ProofAge      int    `json:"proof_age"`
	Accepted      bool   `json:"accepted"`
	Reason        string `json:"reason"`
}
