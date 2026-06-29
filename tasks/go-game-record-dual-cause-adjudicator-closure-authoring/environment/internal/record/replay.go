package record

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"math"
	"sort"
	"strings"
)

type board struct {
	size  int
	cells map[string]string
}

func newBoard(size int) board {
	return board{size: size, cells: map[string]string{}}
}

func (b board) clone() board {
	cells := make(map[string]string, len(b.cells))
	for k, v := range b.cells {
		cells[k] = v
	}
	return board{size: b.size, cells: cells}
}

func (b board) apply(m Move) error {
	if strings.EqualFold(m.Point, "pass") {
		return nil
	}
	point := strings.ToUpper(m.Point)
	if err := validPoint(point, b.size); err != nil {
		return err
	}
	if _, exists := b.cells[point]; exists {
		return fmt.Errorf("point %s is already occupied", point)
	}
	b.cells[point] = m.Color
	return nil
}

func (b board) hash() string {
	keys := make([]string, 0, len(b.cells))
	for k := range b.cells {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	var sb strings.Builder
	fmt.Fprintf(&sb, "size=%d;", b.size)
	for _, k := range keys {
		fmt.Fprintf(&sb, "%s=%s;", k, b.cells[k])
	}
	digest := sha256.Sum256([]byte(sb.String()))
	return hex.EncodeToString(digest[:])
}

func Replay(rec GameRecord, rules Rulebook) (ReplayResult, error) {
	if rec.Ruleset != rules.Ruleset {
		return ReplayResult{}, fmt.Errorf("record %s uses ruleset %s but rulebook is %s", rec.RecordID, rec.Ruleset, rules.Ruleset)
	}
	if rec.BoardSize != rules.BoardSize {
		return ReplayResult{}, fmt.Errorf("record %s board_size %d does not match rulebook %d", rec.RecordID, rec.BoardSize, rules.BoardSize)
	}
	if math.Abs(rec.Komi-rules.Komi) > 0.0001 && !rec.Score.Legacy {
		return ReplayResult{}, fmt.Errorf("record %s komi %.1f does not match rulebook %.1f", rec.RecordID, rec.Komi, rules.Komi)
	}

	mainBoard := newBoard(rec.BoardSize)
	snapshots := map[int]board{0: mainBoard.clone()}
	passes := 0
	var terminal []int
	closed := false
	for i, m := range rec.Main {
		if closed && !strings.EqualFold(m.Point, "pass") {
			return ReplayResult{}, fmt.Errorf("record %s has move %d after terminal passes", rec.RecordID, m.Number)
		}
		if err := mainBoard.apply(m); err != nil {
			return ReplayResult{}, fmt.Errorf("record %s main move %d: %w", rec.RecordID, m.Number, err)
		}
		if strings.EqualFold(m.Point, "pass") {
			passes++
			terminal = append(terminal, m.Number)
		} else {
			passes = 0
			terminal = nil
		}
		if passes == rules.PassesToEnd {
			closed = true
		}
		snapshots[i+1] = mainBoard.clone()
	}
	if passes != rules.PassesToEnd {
		return ReplayResult{}, fmt.Errorf("record %s must end with exactly %d consecutive passes", rec.RecordID, rules.PassesToEnd)
	}

	variationReports := make([]VariationReplay, 0, len(rec.Variations))
	for _, v := range rec.Variations {
		base, ok := snapshots[v.FromMove]
		if !ok {
			return ReplayResult{}, fmt.Errorf("variation %s starts from unavailable main move %d", v.Name, v.FromMove)
		}
		branchBoard := base.clone()
		branchOnly := []string{}
		for _, m := range v.Moves {
			before := branchBoard.clone()
			if err := branchBoard.apply(m); err != nil {
				return ReplayResult{}, fmt.Errorf("record %s variation %s move %d: %w", rec.RecordID, v.Name, m.Number, err)
			}
			if !strings.EqualFold(m.Point, "pass") {
				point := strings.ToUpper(m.Point)
				if _, already := before.cells[point]; !already {
					branchOnly = append(branchOnly, m.Color+":"+point)
				}
			}
		}
		leaks := 0
		for _, item := range branchOnly {
			parts := strings.Split(item, ":")
			if len(parts) == 2 && mainBoard.cells[parts[1]] == parts[0] {
				leaks++
			}
		}
		variationReports = append(variationReports, VariationReplay{Name: v.Name, FromMove: v.FromMove, StateHash: branchBoard.hash(), BranchOnlyMoves: branchOnly, BranchLeakCount: leaks})
	}

	return ReplayResult{
		RecordID:             rec.RecordID,
		Ruleset:              rec.Ruleset,
		MainMoveCount:        len(rec.Main),
		FinalStateHash:       mainBoard.hash(),
		PassesToClose:        passes,
		TerminalPassMoveNums: terminal,
		Winner:               rec.Score.Winner,
		Margin:               rec.Score.Margin,
		LegacyScoreNotation:  rec.Score.Legacy,
		VariationReplays:     variationReports,
	}, nil
}

func validPoint(point string, size int) error {
	if len(point) < 2 {
		return fmt.Errorf("point %s is malformed", point)
	}
	col := int(point[0]-'A') + 1
	row, err := parsePositive(point[1:])
	if err != nil {
		return fmt.Errorf("point %s has malformed row", point)
	}
	if col < 1 || col > size || row < 1 || row > size {
		return fmt.Errorf("point %s is outside %dx%d board", point, size, size)
	}
	return nil
}

func parsePositive(s string) (int, error) {
	value := 0
	for _, r := range s {
		if r < '0' || r > '9' {
			return 0, fmt.Errorf("not numeric")
		}
		value = value*10 + int(r-'0')
	}
	if value <= 0 {
		return 0, fmt.Errorf("not positive")
	}
	return value, nil
}

func roundTenth(v float64) float64 {
	return math.Round(v*10) / 10
}
