package emit

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
)

// ComposeDigestHex derives digest_hex from row components and layout generation.
func ComposeDigestHex(
	dpHex, affHex string,
	spreadIndex, retransmit int,
	layoutGen uint64,
	replayDepth int,
	segmentSeqCRC, layoutTokenHex string,
) string {
	payload := fmt.Sprintf(
		"%s|%s|%d|%d|%d|%d|%s|%s",
		dpHex, affHex, spreadIndex, retransmit, layoutGen, replayDepth, segmentSeqCRC, layoutTokenHex,
	)
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:8])
}

// SessionTokenHex derives a layout correlation token from generation and mask hex fields.
func SessionTokenHex(layoutGen uint64, dpHex, affHex string) string {
	payload := fmt.Sprintf("%d|%s|%s", layoutGen, dpHex, affHex)
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:4])
}
