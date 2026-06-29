package format

// Event is a single replay frame after drift correction.
type Event struct {
	Seq         uint32
	Tick        uint32
	Type        uint16
	Payload     []byte
	ShardID     uint32
	SourceOrder int
}

// ShardMeta records per-shard drift metadata.
type ShardMeta struct {
	ShardID uint32 `json:"shard_id"`
	DriftMs int32  `json:"drift_ms"`
}

// Chronicle is the normalized export document.
type Chronicle struct {
	Version   int          `json:"version"`
	Shards    []ShardMeta  `json:"shards"`
	Events    []EventJSON  `json:"events"`
	Integrity string       `json:"integrity"`
}

// EventJSON is the chronicle wire shape for one event.
type EventJSON struct {
	Seq        uint32 `json:"seq"`
	Tick       uint32 `json:"tick"`
	Type       uint16 `json:"type"`
	PayloadHex string `json:"payload_hex"`
}
