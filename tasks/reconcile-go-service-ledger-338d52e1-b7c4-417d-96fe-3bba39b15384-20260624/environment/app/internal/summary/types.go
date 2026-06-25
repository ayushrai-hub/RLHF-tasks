package summary

type MetricSummary struct {
	Count int     `json:"count"`
	Sum   float64 `json:"sum"`
	Min   float64 `json:"min"`
	Max   float64 `json:"max"`
	Avg   float64 `json:"avg"`
}

type ServiceSummary struct {
	Service    string                   `json:"service"`
	Tier       string                   `json:"tier"`
	EventCount int                      `json:"event_count"`
	Sources    []string                 `json:"sources"`
	Metrics    map[string]MetricSummary `json:"metrics"`
}

type Totals struct {
	ServiceCount  int `json:"service_count"`
	EventCount    int `json:"event_count"`
	DroppedEvents int `json:"dropped_events"`
}

type Report struct {
	Services []ServiceSummary `json:"services"`
	Totals   Totals           `json:"totals"`
}
