package model

type Issue struct {
	Code    string
	Message string
}

type Event struct {
	Seq        int64
	TS         string
	Host       string
	User       string
	Source     string
	Action     string
	Detail     string
	AttackerID string
}

type InitialAccess struct {
	AttackerID    string `json:"attacker_id"`
	Host          string `json:"host"`
	Vector        string `json:"vector"`
	Vulnerability string `json:"vulnerability"`
	Account       string `json:"account"`
	SourceIP      string `json:"source_ip"`
	Timestamp     string `json:"timestamp"`
}

type Exfiltration struct {
	DestinationIP string `json:"destination_ip"`
	Protocol      string `json:"protocol"`
	Bytes         int64  `json:"bytes"`
	Timestamp     string `json:"timestamp"`
}

type TamperedEvent struct {
	Seq       int64  `json:"seq"`
	Host      string `json:"host"`
	User      string `json:"user"`
	ClaimedTS string `json:"claimed_ts"`
	TrueTS    string `json:"true_ts"`
	Detail    string `json:"detail"`
}

type Evidence struct {
	Events            []Event
	InitialAccess     []InitialAccess
	CompromisedHosts  []string
	CompromisedUsers  []string
	Commands          []string
	Persistence       []string
	StolenFiles       []string
	StolenSecrets     []string
	Exfiltration      Exfiltration
	IOCs              []string
	FalseLeads        []string
	TamperedEvents    []TamperedEvent
	ModifiedConfigs   []string
	CfgFlag           bool
	Summary           map[string]int
	SecretDigest      string
}
