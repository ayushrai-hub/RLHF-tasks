package reconcile

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"math"
	"sort"
	"strconv"

	"columnarvalidator/codec/types"
)

func ValidateSegment(seg types.Segment) types.SegmentResult {
	faults := make(map[string]struct{})
	decoded := decodeAllColumns(seg)
	rowCount := 0
	if len(decoded) > 0 {
		names := make([]string, 0, len(decoded))
		for name := range decoded {
			names = append(names, name)
		}
		sort.Strings(names)
		firstLen := len(decoded[names[0]])
		for _, vals := range decoded {
			if len(vals) != firstLen {
				faults["COLUMN_ROW_MISMATCH"] = struct{}{}
			}
		}
		if firstLen > 0 {
			rowCount = firstLen
		}
	}

	for _, col := range seg.Columns {
		switch col.Encoding {
		case "plain":
			if len(col.Values) != seg.RowCount {
				faults["COLUMN_ROW_MISMATCH"] = struct{}{}
			}
		case "dictionary":
			for _, idx := range col.Indices {
				if idx < 0 || idx >= len(col.Dictionary) {
					faults["DICT_INDEX_OOB"] = struct{}{}
				}
			}
			if col.DictionaryRevision > 0 && len(col.DictionarySnapshots) > 0 {
				allowed := snapshotSize(col)
				for _, idx := range col.Indices {
					if idx >= allowed {
						faults["DICT_INCREMENTAL_STALE"] = struct{}{}
					}
				}
			}
			if col.MirrorPlain != nil {
				dec := decodeColumn(col)
				mirror := stringifySlice(col.MirrorPlain)
				if !slicesEqual(dec, mirror) {
					faults["DECODE_DIVERGENCE"] = struct{}{}
				}
			}
		case "rle":
			total := 0
			for _, r := range col.Runs {
				total += r.Length
			}
			if total != seg.RowCount {
				faults["RLE_LENGTH_MISMATCH"] = struct{}{}
			}
		case "bitpack":
			if len(col.Values) != seg.RowCount {
				faults["COLUMN_ROW_MISMATCH"] = struct{}{}
			}
			limit := int(math.Pow(2, float64(col.BitWidth)))
			for _, v := range col.Values {
				iv := toInt64(v)
				if iv < 0 || int(iv) >= limit {
					faults["BITPACK_OVERFLOW"] = struct{}{}
				}
			}
		case "delta":
			if len(col.Deltas) != seg.RowCount {
				faults["COLUMN_ROW_MISMATCH"] = struct{}{}
			}
			if col.ValidatedBase != 0 && col.ValidatedBase != col.Base {
				faults["DELTA_BASE_WRONG"] = struct{}{}
			}
		}
		if col.NullBitmap != nil {
			dec := decodeColumn(col)
			if len(col.NullBitmap) != len(dec) {
				faults["NULL_BITMAP_MISMATCH"] = struct{}{}
			} else {
				for i, bit := range col.NullBitmap {
					isNull := dec[i] == "NULL"
					if bit != isNull {
						faults["NULL_BITMAP_MISMATCH"] = struct{}{}
						break
					}
				}
			}
		}
	}

	for colName, stats := range seg.Statistics {
		vals, ok := decoded[colName]
		if !ok {
			continue
		}
		if !statsMatch(vals, stats) {
			faults["STATS_DRIFT"] = struct{}{}
		}
	}

	for _, col := range seg.Columns {
		if _, ok := seg.Statistics[col.Name]; !ok && seg.SchemaVersion >= 2 {
			faults["SCHEMA_EVOLUTION_GAP"] = struct{}{}
		}
	}

	for _, page := range seg.Pages {
		vals, ok := decoded[page.Column]
		if !ok {
			continue
		}
		want := pageChecksum(page.Column, vals)
		if page.ChecksumHex != want {
			faults["PAGE_CORRUPTION"] = struct{}{}
		}
	}

	if seg.RowGroup != nil && seg.RowGroup.RowCount != seg.RowCount {
		faults["ROW_GROUP_DRIFT"] = struct{}{}
	}
	if seg.Metadata != nil && seg.Metadata.StoredRowCount != seg.RowCount {
		faults["STALE_METADATA"] = struct{}{}
	}
	if seg.Pruning != nil {
		kept := countPredicateRows(seg)
		if kept != seg.Pruning.ExpectedKeptRows {
			faults["PRUNE_COUNT_WRONG"] = struct{}{}
		}
	}
	if seg.Compaction != nil {
		prev := -1
		for _, r := range seg.Compaction.Runs {
			if r.Offset < prev {
				faults["MERGE_ORDER_BROKEN"] = struct{}{}
				break
			}
			prev = r.Offset
		}
	}
	if seg.ParallelEncode != nil {
		seen := map[int]int{}
		for _, slot := range seg.ParallelEncode.Slots {
			if prev, ok := seen[slot.SlotID]; ok && prev != slot.RowIndex {
				faults["PARALLEL_SLOT_COLLISION"] = struct{}{}
				break
			}
			seen[slot.SlotID] = slot.RowIndex
		}
	}

	codes := sortedKeys(faults)
	hash := reconstructionHash(decoded, rowCount)
	return types.SegmentResult{
		SegmentID:             seg.SegmentID,
		IntegrityPass:         len(codes) == 0,
		FaultCodes:            codes,
		DecodedRowCount:       rowCount,
		ReconstructionHashHex: hash,
	}
}

func BuildReport(results []types.SegmentResult) types.Report {
	totals := map[string]int{}
	passing := 0
	for _, r := range results {
		if r.IntegrityPass {
			passing++
		}
		for _, code := range r.FaultCodes {
			totals[code]++
		}
	}
	return types.Report{
		Summary: types.Summary{
			SegmentsAnalyzed: len(results),
			SegmentsPassing:  passing,
			SegmentsFailing:  len(results) - passing,
			FaultCodeTotals:  totals,
		},
		Segments: results,
	}
}

func decodeAllColumns(seg types.Segment) map[string][]string {
	out := map[string][]string{}
	for _, col := range seg.Columns {
		out[col.Name] = decodeColumn(col)
	}
	return out
}

func decodeColumn(col types.Column) []string {
	switch col.Encoding {
	case "plain":
		return stringifySlice(col.Values)
	case "dictionary":
		out := make([]string, 0, len(col.Indices))
		for _, idx := range col.Indices {
			if idx < 0 || idx >= len(col.Dictionary) {
				out = append(out, "INVALID")
				continue
			}
			out = append(out, col.Dictionary[idx])
		}
		return out
	case "rle":
		out := make([]string, 0)
		for _, r := range col.Runs {
			s := stringifyValue(r.Value)
			for i := 0; i < r.Length; i++ {
				out = append(out, s)
			}
		}
		return out
	case "bitpack":
		return stringifySlice(col.Values)
	case "delta":
		return decodeDelta(col)
	default:
		return []string{}
	}
}

func decodeDelta(col types.Column) []string {
	out := make([]string, 0, len(col.Deltas))
	cur := col.Base
	for _, d := range col.Deltas {
		cur += d
		out = append(out, strconv.FormatInt(cur, 10))
	}
	return out
}

func snapshotSize(col types.Column) int {
	allowed := -1
	for _, snap := range col.DictionarySnapshots {
		if snap.Revision < col.DictionaryRevision {
			n := len(snap.Dictionary)
			if allowed < 0 || n < allowed {
				allowed = n
			}
		}
	}
	if allowed < 0 {
		return len(col.Dictionary)
	}
	return allowed
}

func statsMatch(vals []string, stats types.ColStats) bool {
	if stats.NullCount != countNulls(vals) {
		return false
	}
	nonNull := filterNonNull(vals)
	if stats.DistinctCount != distinctCount(nonNull) {
		return false
	}
	if len(nonNull) == 0 {
		return true
	}
	minV := nonNull[0]
	maxV := nonNull[0]
	for _, v := range nonNull[1:] {
		if compareValues(v, minV) < 0 {
			minV = v
		}
		if compareValues(v, maxV) > 0 {
			maxV = v
		}
	}
	return stringifyValue(stats.Min) == minV && stringifyValue(stats.Max) == maxV
}

func countPredicateRows(seg types.Segment) int {
	if seg.Pruning == nil {
		return 0
	}
	decoded := decodeAllColumns(seg)
	vals, ok := decoded[seg.Pruning.PredicateColumn]
	if !ok {
		return 0
	}
	want := stringifyValue(seg.Pruning.PredicateValue)
	count := 0
	for _, v := range vals {
		if v == want {
			count++
		}
	}
	return count
}

func pageChecksum(column string, values []string) string {
	payload := column + ":" + joinComma(values)
	sum := sha256.Sum256([]byte(payload))
	return hex.EncodeToString(sum[:])[:16]
}

func reconstructionHash(decoded map[string][]string, rowCount int) string {
	if rowCount == 0 {
		sum := sha256.Sum256([]byte(""))
		return hex.EncodeToString(sum[:])
	}
	names := make([]string, 0, len(decoded))
	for n := range decoded {
		names = append(names, n)
	}
	sort.Strings(names)
	var rows []string
	for i := 0; i < rowCount; i++ {
		parts := make([]string, 0, len(names))
		for _, n := range names {
			vals := decoded[n]
			v := "NULL"
			if i < len(vals) {
				v = vals[i]
			}
			parts = append(parts, fmt.Sprintf("%s=%s", n, v))
		}
		rows = append(rows, joinPipe(parts))
	}
	sum := sha256.Sum256([]byte(joinSemi(rows)))
	return hex.EncodeToString(sum[:])
}

func sortedKeys(m map[string]struct{}) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	sort.Strings(out)
	if len(out) == 0 {
		return []string{}
	}
	return out
}

func stringifySlice(vals []any) []string {
	out := make([]string, len(vals))
	for i, v := range vals {
		out[i] = stringifyValue(v)
	}
	return out
}

func stringifyValue(v any) string {
	if v == nil {
		return "NULL"
	}
	switch t := v.(type) {
	case string:
		return t
	case float64:
		if t == math.Trunc(t) {
			return strconv.FormatInt(int64(t), 10)
		}
		return strconv.FormatFloat(t, 'f', -1, 64)
	case json.Number:
		return t.String()
	default:
		return fmt.Sprint(v)
	}
}

func toInt64(v any) int64 {
	switch t := v.(type) {
	case float64:
		return int64(t)
	case int:
		return int64(t)
	case int64:
		return t
	default:
		return 0
	}
}

func countNulls(vals []string) int {
	n := 0
	for _, v := range vals {
		if v == "NULL" {
			n++
		}
	}
	return n
}

func filterNonNull(vals []string) []string {
	out := make([]string, 0, len(vals))
	for _, v := range vals {
		if v != "NULL" {
			out = append(out, v)
		}
	}
	return out
}

func distinctCount(vals []string) int {
	seen := map[string]struct{}{}
	for _, v := range vals {
		seen[v] = struct{}{}
	}
	return len(seen)
}

func compareValues(a, b string) int {
	ai, aErr := strconv.ParseInt(a, 10, 64)
	bi, bErr := strconv.ParseInt(b, 10, 64)
	if aErr == nil && bErr == nil {
		switch {
		case ai < bi:
			return -1
		case ai > bi:
			return 1
		default:
			return 0
		}
	}
	switch {
	case a < b:
		return -1
	case a > b:
		return 1
	default:
		return 0
	}
}

func slicesEqual(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	for i := range a {
		if a[i] != b[i] {
			return false
		}
	}
	return true
}

func joinComma(vals []string) string {
	return joinWith(vals, ",")
}

func joinPipe(vals []string) string {
	return joinWith(vals, "|")
}

func joinSemi(vals []string) string {
	return joinWith(vals, ";")
}

func joinWith(vals []string, sep string) string {
	if len(vals) == 0 {
		return ""
	}
	out := vals[0]
	for i := 1; i < len(vals); i++ {
		out += sep + vals[i]
	}
	return out
}
