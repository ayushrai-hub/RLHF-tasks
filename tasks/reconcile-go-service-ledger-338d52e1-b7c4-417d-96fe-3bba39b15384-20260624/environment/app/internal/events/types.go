package events

type Event struct {
	EventID      string  `json:"event_id"`
	Service      string  `json:"service"`
	OccurredAt   string  `json:"occurred_at"`
	Metric       string  `json:"metric"`
	Value        float64 `json:"value"`
	Source       string  `json:"source"`
	Sequence     int     `json:"sequence"`
	Kind         string  `json:"kind"`
	CorrectionOf string  `json:"correction_of"`
}
