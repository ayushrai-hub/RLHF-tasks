package models

type HeaderMatch struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

type BackendRule struct {
	Name     string       `json:"name"`
	Weight   int          `json:"weight"`
	Headers  []HeaderMatch `json:"headers,omitempty"`
}

type SplitConfig struct {
	DefaultBackend string       `json:"default_backend"`
	Backends       []BackendRule `json:"backends"`
}

type Request struct {
	ID      string            `json:"id"`
	Headers map[string]string `json:"headers"`
}

type RoutingResult struct {
	RequestID  string `json:"request_id"`
	Backend    string `json:"backend"`
	RuleName   string `json:"rule_name"`
}

type Summary struct {
	TotalRequests  int                `json:"total_requests"`
	BackendCounts  map[string]int     `json:"backend_counts"`
	ExpectedWeights map[string]int    `json:"expected_weights"`
	Balanced       bool               `json:"balanced"`
}

type OutputReport struct {
	RoutedRequests []RoutingResult `json:"routed_requests"`
	Summary        Summary         `json:"summary"`
}
