package record

import (
	"bufio"
	"fmt"
	"os"
	"regexp"
	"strconv"
	"strings"
)

var variationRE = regexp.MustCompile(`^variation\s+([A-Za-z0-9_.-]+)\s+from\s+([0-9]+):$`)

func ParseFile(path string) (GameRecord, error) {
	f, err := os.Open(path)
	if err != nil {
		return GameRecord{}, err
	}
	defer f.Close()

	rec := GameRecord{Path: path}
	mode := "header"
	var current *Variation
	scanner := bufio.NewScanner(f)
	lineNo := 0
	for scanner.Scan() {
		lineNo++
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if idx := strings.Index(line, " #"); idx >= 0 {
			line = strings.TrimSpace(line[:idx])
		}
		switch {
		case line == "main:":
			if current != nil {
				return GameRecord{}, fmt.Errorf("line %d: main section cannot begin inside variation %q", lineNo, current.Name)
			}
			mode = "main"
			continue
		case line == "endvariation":
			if current == nil {
				return GameRecord{}, fmt.Errorf("line %d: endvariation without variation", lineNo)
			}
			rec.Variations = append(rec.Variations, *current)
			current = nil
			mode = "main"
			continue
		case strings.HasPrefix(line, "variation "):
			if mode != "main" || current != nil {
				return GameRecord{}, fmt.Errorf("line %d: variation must start from the main line", lineNo)
			}
			m := variationRE.FindStringSubmatch(line)
			if m == nil {
				return GameRecord{}, fmt.Errorf("line %d: malformed variation header", lineNo)
			}
			from, _ := strconv.Atoi(m[2])
			current = &Variation{Name: m[1], FromMove: from}
			mode = "variation"
			continue
		}

		if strings.HasPrefix(line, "score ") {
			if current != nil {
				return GameRecord{}, fmt.Errorf("line %d: score appears before variation %q is closed", lineNo, current.Name)
			}
			score, err := parseScore(line, rec.Komi)
			if err != nil {
				return GameRecord{}, fmt.Errorf("line %d: %w", lineNo, err)
			}
			rec.Score = score
			continue
		}
		if strings.HasPrefix(line, "result ") {
			if current != nil {
				return GameRecord{}, fmt.Errorf("line %d: result appears before variation %q is closed", lineNo, current.Name)
			}
			rec.ResultRaw = strings.TrimSpace(strings.TrimPrefix(line, "result "))
			continue
		}

		if strings.Contains(line, ":") && mode == "header" {
			key, value, _ := strings.Cut(line, ":")
			if err := setHeader(&rec, strings.TrimSpace(key), strings.TrimSpace(value), lineNo); err != nil {
				return GameRecord{}, err
			}
			continue
		}

		mv, err := parseMove(line)
		if err != nil {
			return GameRecord{}, fmt.Errorf("line %d: %w", lineNo, err)
		}
		if current != nil {
			current.Moves = append(current.Moves, mv)
		} else if mode == "main" {
			rec.Main = append(rec.Main, mv)
		} else {
			return GameRecord{}, fmt.Errorf("line %d: move outside main section", lineNo)
		}
	}
	if err := scanner.Err(); err != nil {
		return GameRecord{}, err
	}
	if current != nil {
		return GameRecord{}, fmt.Errorf("variation %q from move %d is not closed with endvariation", current.Name, current.FromMove)
	}
	if rec.RecordID == "" || rec.Ruleset == "" || rec.BoardSize == 0 || len(rec.Main) == 0 || rec.Score.Raw == "" || rec.ResultRaw == "" {
		return GameRecord{}, fmt.Errorf("record %s is missing required header, main, score, or result content", path)
	}
	if !sameResult(rec.Score.Winner, rec.Score.Margin, rec.ResultRaw) {
		return GameRecord{}, fmt.Errorf("record %s declares result %s but score resolves to %s+%.1f", path, rec.ResultRaw, rec.Score.Winner, rec.Score.Margin)
	}
	return rec, nil
}

func setHeader(rec *GameRecord, key, value string, lineNo int) error {
	switch key {
	case "record_id":
		rec.RecordID = value
	case "ruleset":
		rec.Ruleset = value
	case "board_size":
		n, err := strconv.Atoi(value)
		if err != nil {
			return fmt.Errorf("line %d: board_size must be an integer", lineNo)
		}
		rec.BoardSize = n
	case "komi":
		v, err := strconv.ParseFloat(value, 64)
		if err != nil {
			return fmt.Errorf("line %d: komi must be numeric", lineNo)
		}
		rec.Komi = v
	default:
		return fmt.Errorf("line %d: unknown header %q", lineNo, key)
	}
	return nil
}

func parseMove(line string) (Move, error) {
	fields := strings.Fields(line)
	if len(fields) != 3 {
		return Move{}, fmt.Errorf("move must have number, color, and point")
	}
	n, err := strconv.Atoi(fields[0])
	if err != nil {
		return Move{}, fmt.Errorf("move number must be numeric")
	}
	color := strings.ToUpper(fields[1])
	if color != "B" && color != "W" {
		return Move{}, fmt.Errorf("move color must be B or W")
	}
	point := strings.ToUpper(fields[2])
	return Move{Number: n, Color: color, Point: point}, nil
}

func parseScore(line string, komi float64) (Score, error) {
	raw := strings.TrimSpace(strings.TrimPrefix(line, "score "))
	fields := strings.Fields(raw)
	if len(fields) == 1 && strings.Contains(fields[0], "+") {
		winner, margin, ok := parseResultToken(fields[0])
		if !ok {
			return Score{}, fmt.Errorf("legacy score token is malformed")
		}
		return Score{Legacy: true, Winner: winner, Margin: margin, Raw: raw}, nil
	}
	values := map[string]int{}
	for _, field := range fields {
		key, rawValue, ok := strings.Cut(field, "=")
		if !ok {
			return Score{}, fmt.Errorf("area score fields must use key=value")
		}
		value, err := strconv.Atoi(rawValue)
		if err != nil {
			return Score{}, fmt.Errorf("area score field %s must be an integer", key)
		}
		values[key] = value
	}
	black, okB := values["black_area"]
	white, okW := values["white_area"]
	if !okB || !okW {
		return Score{}, fmt.Errorf("area score requires black_area and white_area")
	}
	diff := float64(black-white) - komi
	winner := "B"
	if diff < 0 {
		winner = "W"
		diff = -diff
	}
	return Score{Legacy: false, BlackArea: black, WhiteArea: white, Winner: winner, Margin: roundTenth(diff), Raw: raw}, nil
}

func parseResultToken(token string) (string, float64, bool) {
	winner, rest, ok := strings.Cut(strings.ToUpper(token), "+")
	if !ok || (winner != "B" && winner != "W") {
		return "", 0, false
	}
	margin, err := strconv.ParseFloat(rest, 64)
	if err != nil {
		return "", 0, false
	}
	return winner, roundTenth(margin), true
}

func sameResult(winner string, margin float64, token string) bool {
	w, m, ok := parseResultToken(token)
	return ok && w == winner && roundTenth(m) == roundTenth(margin)
}
