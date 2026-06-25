package types

import (
	"strconv"
	"unicode"
)

// Probe is one captured TWAMP measurement after canonicalization.
type Probe struct {
	ProbeID       string
	SessionID     string
	CycleID       int64
	ReflectorID   string
	SendTsUs      int64
	RecvTsUs      int64
	TxTsUs        int64
	SeqNo         int64
	RecvMinusSend int64
	LossFlag      bool
	OwdUs         int64
	ShardOrder    int
	Verdict       string
	Survived      bool
}

// Reflector is one row of the reflector registry.
type Reflector struct {
	ReflectorID string `json:"reflector_id"`
	Station     string `json:"station"`
	Class       string `json:"class"`
}

// Config is the parsed control file.
type Config struct {
	ValidityWindowStartUs int64  `json:"validity_window_start_us"`
	ValidityWindowEndUs   int64  `json:"validity_window_end_us"`
	StaleMaxUs            int64  `json:"stale_max_us"`
	OwdAnomalyThresholdUs int64  `json:"owd_anomaly_threshold_us"`
	JitterFlagUs          int64  `json:"jitter_flag_us"`
	Secret                string `json:"secret"`
}

// Marker is one operator marker after seal validation.
type Marker struct {
	MarkerID      string
	Kind          string
	CycleID       int64
	ReflectorID   string
	WindowOpenUs  int64
	WindowCloseUs int64
	Seal          string
	Valid         bool
}

// CycleRow is one cycles[] entry in the report.
type CycleRow struct {
	CycleID        int64
	ProbeCount     int
	LossCount      int
	AnomalyCount   int
	ThresholdOwdUs int64
	Contributors   []string
}

// ReflectorRow is one reflectors[] entry in the report.
type ReflectorRow struct {
	ReflectorID           string
	Station               string
	Class                 string
	ProbeCount            int
	AnomalyCount          int
	QuietPeriodSuppressed int
	OfflineObserved       bool
	JitterSharePermille   int64
}

// ProbeRow is one probes[] entry in the report.
type ProbeRow struct {
	ProbeID     string
	SessionID   string
	CycleID     int64
	ReflectorID string
	OwdUs       int64
	Verdict     string
}

// Summary block.
type Summary struct {
	TotalProbes         int
	AlignedGood         int
	Cycles              int
	ByVerdict           map[string]int
	JitterSharePermille map[string]int64
	ReportDigest        string
}

// Report is the top-level emitted structure.
type Report struct {
	SchemaVersion string
	Summary       Summary
	Reflectors    []ReflectorRow
	Cycles        []CycleRow
	Probes        []ProbeRow
	ReportDigest  string
}

// NumericSuffix returns the longest trailing digit run of s as an int64.
// An identifier with no trailing digits returns 0.
func NumericSuffix(s string) int64 {
	end := len(s)
	start := end
	for start > 0 && unicode.IsDigit(rune(s[start-1])) {
		start--
	}
	if start == end {
		return 0
	}
	n, err := strconv.ParseInt(s[start:end], 10, 64)
	if err != nil {
		return 0
	}
	return n
}

// SuffixLess sorts by numeric suffix asc, lex within ties.
func SuffixLess(a, b string) bool {
	na, nb := NumericSuffix(a), NumericSuffix(b)
	if na != nb {
		return na < nb
	}
	return a < b
}
