package model

type Scenario struct {
	Name           string              `json:"name"`
	FreshnessBound int                 `json:"freshness_bound"`
	Resources      []Resource          `json:"resources"`
	Snapshots      []DirectorySnapshot `json:"snapshots"`
	Steps          []Step              `json:"steps"`
}

type Step struct {
	Op       string `json:"op"`
	Tick     int    `json:"tick"`
	Revision int    `json:"revision,omitempty"`
	Username string `json:"username,omitempty"`
	Resource string `json:"resource,omitempty"`
	Action   string `json:"action,omitempty"`
}
