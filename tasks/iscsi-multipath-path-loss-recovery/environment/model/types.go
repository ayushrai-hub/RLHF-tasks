package model

// Context carries one bundled pack scenario.
type Context struct {
	ScenarioLabel      string
	TableGen      uint64
	CrashMid       bool
	ActivePathMask  uint64
	TargetPathMask     uint64
	StrandedPathMask   uint64
	AluaBaseMs int
	FlushBump int
	FailbackEarly bool
	SummaryGreenView bool
	RetainSeq      int
	GateHold       bool
}

// Segment is one durable checkpoint fragment.
type Segment struct {
	Kind string
	Mask uint64
	Seq  int
}

// Ledger holds partial writes across reshuffle.
type Ledger struct {
	ActivePathMask uint64
	AffinityMask  uint64
	Segments      []Segment
	Finalized     bool
	Replayed      bool
	ReplayEpoch   int
	StagingDepth  int
}

// RouteTable holds persisted vector routing state.
type RouteTable struct {
	AffinityMask uint64
	Routed       bool
}

// SpreadView captures plane metric inputs.
type SpreadView struct {
	SpreadIndex int
	EvenLooking bool
}

// Limits bounds replay work per pack.
type Limits struct {
	MaxSegments int
}

// ReplayResult summarizes replay completion.
type ReplayResult struct {
	Ordered bool
	Depth   int
}

// Row is one path failback report observation record.
type Row struct {
	ScenarioLabel        string `json:"scenario_label"`
	PathOverlapIndex   int    `json:"path_overlap_index"`
	ActivePathHex string `json:"active_path_hex"`
	StandbyPathHex  string `json:"standby_path_hex"`
	AluaReprobeMs  int    `json:"alua_reprobe_ms"`
	DigestHex        string `json:"digest_hex"`
	ReplayEpoch      int    `json:"replay_epoch"`
	SegmentSeqCRC    string `json:"segment_seq_crc"`
	SessionTokenHex   string `json:"session_token_hex"`
}

// Envelope is the top-level path failback report document.
type Envelope struct {
	Runs []Row `json:"runs"`
}
