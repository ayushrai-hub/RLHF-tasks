package emit

import "pathfb/model"

// BuildRow assembles one path failback report observation record.
func BuildRow(
	packLabel string,
	spreadIndex int,
	dpHex string,
	affHex string,
	retransmit int,
	layoutGen uint64,
	replayDepth int,
	segmentSeqCRC string,
) model.Row {
	layoutToken := SessionTokenHex(layoutGen, dpHex, affHex)
	return model.Row{
		ScenarioLabel:        packLabel,
		PathOverlapIndex:   spreadIndex,
		ActivePathHex: dpHex,
		StandbyPathHex:  affHex,
		AluaReprobeMs:  retransmit,
		ReplayEpoch:      replayDepth,
		SegmentSeqCRC:    segmentSeqCRC,
		SessionTokenHex:   layoutToken,
		DigestHex: ComposeDigestHex(
			dpHex, affHex, spreadIndex, retransmit, layoutGen,
			replayDepth, segmentSeqCRC, layoutToken,
		),
	}
}

// BuildEnvelope wraps rows for JSON emission.
func BuildEnvelope(rows []model.Row) model.Envelope {
	return model.Envelope{Runs: rows}
}
