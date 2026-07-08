package model

type ServiceLine struct {
	LXSequence        int      `json:"lx_sequence"`
	Procedure         string   `json:"procedure"`
	Charge            string   `json:"charge"`
	DiagnosisPointers []string `json:"diagnosis_pointers"`
}

type Claim struct {
	ControlNumber string        `json:"control_number"`
	PatientName   string        `json:"patient_name"`
	SubscriberID  string        `json:"subscriber_id"`
	TotalCharge   string        `json:"total_charge"`
	FrequencyCode string        `json:"frequency_code"`
	RefF8         string        `json:"-"`
	ServiceLines  []ServiceLine `json:"service_lines"`
	Priority      int           `json:"-"`
}

type Summary struct {
	ClaimCount          int    `json:"claim_count"`
	ServiceLineCount    int    `json:"service_line_count"`
	SkippedSegments     int    `json:"skipped_segments"`
	ManifestFingerprint string `json:"manifest_fingerprint,omitempty"`
	ErrorsDigest        string `json:"errors_digest,omitempty"`
	ExportEpoch         int    `json:"export_epoch,omitempty"`
}

type WovenOutput struct {
	Claims []Claim `json:"claims"`
}
