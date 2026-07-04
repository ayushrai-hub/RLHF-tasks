package audit

import (
	"encoding/json"
	"os"
	"path/filepath"

	"example.com/registeraudit/internal/chain"
	"example.com/registeraudit/internal/codec"
	"example.com/registeraudit/internal/scan"
	"example.com/registeraudit/internal/seal"
)

const slaveAllowlistPath = "/app/environment/data/slave_allowlist.txt"

type Report struct {
	APIVersion         int      `json:"api_version"`
	Segment            int      `json:"segment"`
	MregFiles          []string `json:"mreg_files"`
	FrameCount         int      `json:"frame_count"`
	RegisterReadCount  int      `json:"register_read_count"`
	CrcFailureCount    int      `json:"crc_failure_count"`
	ExceptionCount     int      `json:"exception_count"`
	ChainRootHex       string   `json:"chain_root_hex"`
	DuplicateSeqDrops  int      `json:"duplicate_seq_drops"`
	SlaveRejectCount   int      `json:"slave_reject_count"`
	CheckpointSkipCount int     `json:"checkpoint_skip_count"`
	MinReg             int      `json:"min_reg"`
	MaxReg             int      `json:"max_reg"`
	ActiveSlaveCount   int      `json:"active_slave_count"`
}

func Run(dir string, segment int, outPath string) error {
	names, frames, crcFails, err := scan.LoadDir(dir)
	if err != nil {
		return err
	}
	_ = crcFails
	allowed, err := scan.LoadSlaveAllowlist(slaveAllowlistPath)
	if err != nil {
		return err
	}

	var kept []codec.Frame
	for _, fr := range frames {
		if int(fr.Segment) != segment {
			kept = append(kept, fr)
			continue
		}
		if !scan.SlaveAllowed(fr.Slave, allowed) {
			continue
		}
		kept = append(kept, fr)
	}
	collapsed, drops := scan.CollapseSeq(kept)
	root, err := chain.Root(collapsed)
	if err != nil {
		return err
	}
	_ = seal.SeedPrior(dir, filepath.Dir(outPath))

	regReads := 0
	exceptions := 0
	slaves := map[uint8]struct{}{}
	for _, fr := range collapsed {
		if fr.Func == 0x03 {
			regReads += int(fr.Count)
			slaves[fr.Slave] = struct{}{}
		}
		if fr.Func >= 0x80 {
			exceptions++
		}
	}
	minReg, maxReg := scan.SummarizeRegSpan(kept)

	rep := Report{
		APIVersion:         1,
		Segment:            segment,
		MregFiles:          names,
		FrameCount:         len(collapsed),
		RegisterReadCount:  regReads,
		CrcFailureCount:    0,
		ExceptionCount:     exceptions,
		ChainRootHex:       root,
		DuplicateSeqDrops:  drops,
		SlaveRejectCount:   0,
		CheckpointSkipCount: 0,
		MinReg:             minReg,
		MaxReg:             maxReg,
		ActiveSlaveCount:   len(slaves),
	}
	wrap := map[string]any{"debug": true, "report": rep}
	raw, err := json.MarshalIndent(wrap, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(outPath, raw, 0o644)
}
