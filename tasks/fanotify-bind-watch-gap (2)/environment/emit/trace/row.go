package trace

type Row struct {
	Scenario       string `json:"scenario"`
	WaveGen        int    `json:"wave_gen"`
	EdgeFPHost     string `json:"edge_fp_host"`
	EdgeFPWork     string `json:"edge_fp_work"`
	MissGap        int64  `json:"miss_gap"`
	GenSkew        int64  `json:"gen_skew"`
	RetentionStamp string `json:"retention_stamp"`
	RowSeal        string `json:"row_seal"`
}

type Envelope struct {
	Runs         []Row  `json:"runs"`
	ReportDigest string `json:"report_digest"`
	ReplayToken  string `json:"replay_token"`
}
