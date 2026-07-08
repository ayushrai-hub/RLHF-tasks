package types

type Run struct {
	Value  any `json:"value"`
	Length int `json:"length"`
}

type DictSnapshot struct {
	Revision   int      `json:"revision"`
	Dictionary []string `json:"dictionary"`
}

type Column struct {
	Name                string         `json:"name"`
	Encoding            string         `json:"encoding"`
	LogicalType         string         `json:"logical_type"`
	Values              []any          `json:"values,omitempty"`
	Dictionary          []string       `json:"dictionary,omitempty"`
	Indices             []int          `json:"indices,omitempty"`
	DictionaryRevision  int            `json:"dictionary_revision,omitempty"`
	DictionarySnapshots []DictSnapshot `json:"dictionary_snapshots,omitempty"`
	Runs                []Run          `json:"runs,omitempty"`
	BitWidth            int            `json:"bit_width,omitempty"`
	Base                int64          `json:"base,omitempty"`
	ValidatedBase       int64          `json:"validated_base,omitempty"`
	Deltas              []int64        `json:"deltas,omitempty"`
	MirrorPlain         []any          `json:"mirror_plain,omitempty"`
	NullBitmap          []bool         `json:"null_bitmap,omitempty"`
}

type Page struct {
	PageID      int    `json:"page_id"`
	Column      string `json:"column"`
	ChecksumHex string `json:"checksum_hex"`
}

type ColStats struct {
	Min           any `json:"min"`
	Max           any `json:"max"`
	NullCount     int `json:"null_count"`
	DistinctCount int `json:"distinct_count"`
}

type RowGroup struct {
	RowCount int `json:"row_count"`
}

type Metadata struct {
	StoredRowCount int `json:"stored_row_count"`
}

type Pruning struct {
	PredicateColumn   string `json:"predicate_column"`
	PredicateValue    any    `json:"predicate_value"`
	ExpectedKeptRows  int    `json:"expected_kept_rows"`
}

type CompactionRun struct {
	Offset int `json:"offset"`
	Length int `json:"length"`
}

type Compaction struct {
	Runs []CompactionRun `json:"runs"`
}

type ParallelSlot struct {
	SlotID    int `json:"slot_id"`
	RowIndex  int `json:"row_index"`
}

type ParallelEncode struct {
	Slots []ParallelSlot `json:"slots"`
}

type Segment struct {
	SegmentID     string                    `json:"segment_id"`
	RowCount      int                       `json:"row_count"`
	SchemaVersion int                       `json:"schema_version"`
	Columns       []Column                  `json:"columns"`
	Pages         []Page                    `json:"pages"`
	Statistics    map[string]ColStats       `json:"statistics"`
	RowGroup      *RowGroup                 `json:"row_group,omitempty"`
	Metadata      *Metadata                 `json:"metadata,omitempty"`
	Pruning       *Pruning                  `json:"pruning,omitempty"`
	Compaction    *Compaction               `json:"compaction,omitempty"`
	ParallelEncode *ParallelEncode          `json:"parallel_encode,omitempty"`
}

type Summary struct {
	SegmentsAnalyzed int            `json:"segments_analyzed"`
	SegmentsPassing  int            `json:"segments_passing"`
	SegmentsFailing  int            `json:"segments_failing"`
	FaultCodeTotals  map[string]int `json:"fault_code_totals"`
}

type SegmentResult struct {
	SegmentID             string   `json:"segment_id"`
	IntegrityPass         bool     `json:"integrity_pass"`
	FaultCodes            []string `json:"fault_codes"`
	DecodedRowCount       int      `json:"decoded_row_count"`
	ReconstructionHashHex string   `json:"reconstruction_hash_hex"`
}

type Report struct {
	Summary  Summary         `json:"summary"`
	Segments []SegmentResult `json:"segments"`
}
