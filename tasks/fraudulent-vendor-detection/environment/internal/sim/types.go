package sim

type LimitRow struct {
	AccountID string `json:"vendor_id"`
	Ceiling  int64  `json:"vendor_graph_cap"`
}

type Invoice struct {
	LineID string `json:"invoice_id"`
	AccountID string `json:"vendor_id"`
	Tick     int64  `json:"period"`
	Stream     int    `json:"stage"`
	Cents    int64  `json:"weight_pts"`
}

type FleetFixture struct {
	FleetID  string     `json:"panel_id"`
	Limits  []LimitRow `json:"limits"`
	Lines []Invoice   `json:"lines"`
}
