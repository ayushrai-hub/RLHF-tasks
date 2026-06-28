package api

// Event is one logical append after WAL verification.
type Event struct {
	Lamport  uint64 `json:"lamport"`
	NodeID   uint32 `json:"node_id"`
	Seq      uint32 `json:"seq"`
	Payload  []byte `json:"-"`
	PayloadHex string `json:"payload_hex,omitempty"`
}

// Frame is an on-disk WAL record.
type Frame struct {
	Lamport  uint64 `json:"lamport"`
	NodeID   uint32 `json:"node_id"`
	Seq      uint32 `json:"seq"`
	Payload  []byte `json:"-"`
	PayloadHex string `json:"payload_hex"`
	CRC      uint32 `json:"crc"`
}

// HeaderBytes returns the canonical big-endian header for integrity:
// uint64 lamport, uint32 node_id, uint32 seq (network byte order).
func HeaderBytes(fr Frame) []byte {
	buf := make([]byte, 16)
	putU64BE(buf[0:], fr.Lamport)
	putU32BE(buf[8:], fr.NodeID)
	putU32BE(buf[12:], fr.Seq)
	return buf
}

func putU64BE(b []byte, v uint64) {
	b[0] = byte(v >> 56)
	b[1] = byte(v >> 48)
	b[2] = byte(v >> 40)
	b[3] = byte(v >> 32)
	b[4] = byte(v >> 24)
	b[5] = byte(v >> 16)
	b[6] = byte(v >> 8)
	b[7] = byte(v)
}

func putU32BE(b []byte, v uint32) {
	b[0] = byte(v >> 24)
	b[1] = byte(v >> 16)
	b[2] = byte(v >> 8)
	b[3] = byte(v)
}

// CanonicalRecordBytes is the byte form fed into the pack digest hasher
// for each merged event: HeaderBytes for the event fields plus raw payload.
func CanonicalRecordBytes(ev Event) []byte {
	fr := Frame{Lamport: ev.Lamport, NodeID: ev.NodeID, Seq: ev.Seq}
	out := make([]byte, 0, 16+len(ev.Payload))
	out = append(out, HeaderBytes(fr)...)
	out = append(out, ev.Payload...)
	return out
}

// Merge tie-break (documented contract): when two events share the same
// logical clock (lamport), the event with the higher NodeID is ordered first
// (appears earlier in the merged stream).

type NodeState struct {
	NodeID          uint32 `json:"node_id"`
	Partitioned     bool   `json:"partitioned"`
	PartitionEpoch  int    `json:"partition_epoch"`
}

type Scenario struct {
	ID          string               `json:"id"`
	MergeMode   string               `json:"merge_mode"`
	HealEpoch   int                  `json:"heal_epoch"`
	QuorumNeed  int                  `json:"quorum_need"`
	Nodes       []NodeState          `json:"nodes"`
	Frames      map[string][]Frame   `json:"frames_by_node"`
}

type Pack struct {
	SchemaVersion     int        `json:"schema_version"`
	RecoveryBudgetMS  int        `json:"recovery_budget_ms"`
	Scenarios         []Scenario `json:"scenarios"`
}

type ScenarioReport struct {
	CanonicalDigestHex string `json:"canonical_digest_hex"`
	RecoveredEvents    int    `json:"recovered_events"`
	QuorumSizeSeen     int    `json:"quorum_size_seen"`
	RecoveryElapsedMS  int    `json:"recovery_elapsed_ms"`
	DataLossEvents     int    `json:"data_loss_events"`
	PartitionHealed    bool   `json:"partition_healed"`
	MergeMode          string `json:"merge_mode"`
}

type Report struct {
	SchemaVersion    int                       `json:"schema_version"`
	RecoveryBudgetMS int                       `json:"recovery_budget_ms"`
	Scenarios        map[string]ScenarioReport `json:"scenarios"`
}
