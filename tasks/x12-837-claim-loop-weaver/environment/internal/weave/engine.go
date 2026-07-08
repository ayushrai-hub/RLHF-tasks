package weave

import (
	"encoding/json"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"claim-weaver/internal/edi"
	"claim-weaver/internal/staging"
)

type claimState struct {
	ControlNumber string
	Priority      int
	CLMFields     []string
	PatientName   string
	SubscriberID  string
	RefF8         string
	CompSep       byte
	Lines         map[int]*lineState
}

type Engine struct {
	Claims  map[string]*claimState
	Errors  []string
	Skipped int
}

func NewEngine() *Engine {
	return &Engine{Claims: make(map[string]*claimState)}
}

func (engine *Engine) LoadManifest(path string) (map[string]int, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	out := make(map[string]int)
	if err := json.Unmarshal(data, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func (engine *Engine) ProcessShards(shardsDir string, manifest map[string]int) error {
	paths, err := filepath.Glob(filepath.Join(shardsDir, "*.edi"))
	if err != nil {
		return err
	}
	sort.Strings(paths)

	claimOrder := make([]string, 0)

	for _, shardPath := range paths {
		base := filepath.Base(shardPath)
		priority := manifest[base]
		raw, err := os.ReadFile(shardPath)
		if err != nil {
			return err
		}
		segments := edi.SplitSegments(string(raw))
		if len(segments) == 0 {
			continue
		}

		elemSep := edi.ElementSeparator(segments[0])
		compSep := edi.ComponentSeparator(segments[0])

		var currentClaim string
		var currentLX int
		var inherited []string

		for _, segRaw := range segments {
			seg := edi.ParseSegment(segRaw, elemSep)
			switch seg.ID {
			case "ISA":
				elemSep = edi.ElementSeparator(segRaw)
				compSep = edi.ComponentSeparator(segRaw)
				continue
			case "CLM":
				if len(seg.Fields) < 2 || seg.Fields[1] == "" {
					engine.logSkip(base, segRaw)
					continue
				}
				currentClaim = seg.Fields[1]
				currentLX = 0
				inherited = nil
				claim := engine.ensureClaim(currentClaim, priority, seg.Fields)
				if priority >= claim.Priority {
					claim.Priority = priority
					claim.CLMFields = seg.Fields
					claim.CompSep = compSep
				}
				claimOrder = appendClaimOrder(claimOrder, currentClaim)
			case "NM1":
				if len(seg.Fields) < 4 {
					engine.logSkip(base, segRaw)
					continue
				}
				qual := seg.Fields[1]
				if qual != "QC" && qual != "IL" && qual != "82" && qual != "85" {
					engine.logSkip(base, segRaw)
					continue
				}
				if currentClaim == "" {
					continue
				}
				claim := engine.Claims[currentClaim]
				if priority < claim.Priority {
					continue
				}
				if qual == "QC" {
					last := normalizeName(seg.Fields[3])
					first := ""
					if len(seg.Fields) > 4 {
						first = seg.Fields[4]
					}
					claim.PatientName = strings.TrimSpace(last + " " + first)
				} else if qual == "IL" && len(seg.Fields) > 9 {
					claim.SubscriberID = seg.Fields[9]
				}
			case "REF":
				if currentClaim == "" {
					continue
				}
				claim := engine.Claims[currentClaim]
				if priority < claim.Priority {
					continue
				}
				if len(seg.Fields) > 2 && seg.Fields[1] == "F8" {
					claim.RefF8 = seg.Fields[2]
				}
			case "LX":
				if len(seg.Fields) < 2 || !isPositiveInt(seg.Fields[1]) {
					engine.logSkip(base, segRaw)
					continue
				}
				if currentClaim == "" {
					engine.logSkip(base, segRaw)
					continue
				}
				currentLX = atoi(seg.Fields[1])
				claim := engine.Claims[currentClaim]
				line := engine.ensureLine(claim, currentLX, priority, inherited)
				if priority >= line.Priority {
					line.Priority = priority
					line.InheritedPointers = append([]string(nil), inherited...)
				}
			case "SV1":
				if len(seg.Fields) < 2 || ParseProcedure(seg.Fields, compSep) == "" {
					engine.logSkip(base, segRaw)
					continue
				}
				if currentClaim == "" || currentLX == 0 {
					engine.logSkip(base, segRaw)
					continue
				}
				claim := engine.Claims[currentClaim]
				line := engine.ensureLine(claim, currentLX, priority, inherited)
				if priority >= line.Priority {
					line.Priority = priority
					line.SV1Fields = seg.Fields
				}
			case "HI":
				if currentClaim == "" || currentLX == 0 {
					continue
				}
				claim := engine.Claims[currentClaim]
				line := engine.ensureLine(claim, currentLX, priority, inherited)
				if priority >= line.Priority {
					line.Priority = priority
					line.HICodes = parseHICodes(seg.Fields, compSep)
					inherited = UpdateInherited(line.HICodes)
				}
			}
		}
	}
	return nil
}

func (engine *Engine) BuildSnapshot() staging.WeaveSnapshot {
	keys := make([]string, 0, len(engine.Claims))
	for control := range engine.Claims {
		keys = append(keys, control)
	}
	sort.Strings(keys)

	claims := make([]staging.ClaimSnapshot, 0, len(keys))
	for _, control := range keys {
		claim := engine.Claims[control]
		if claim == nil {
			continue
		}
		lineMap := make(map[int]staging.LineSnapshot, len(claim.Lines))
		lxKeys := make([]int, 0, len(claim.Lines))
		for lx := range claim.Lines {
			lxKeys = append(lxKeys, lx)
		}
		sort.Ints(lxKeys)
		for _, lx := range lxKeys {
			line := claim.Lines[lx]
			lineMap[lx] = staging.LineSnapshot{
				LXSequence:        line.LXSequence,
				Priority:          line.Priority,
				SV1Fields:         line.SV1Fields,
				HICodes:           line.HICodes,
				InheritedPointers: line.InheritedPointers,
			}
		}
		claims = append(claims, staging.ClaimSnapshot{
			ControlNumber: claim.ControlNumber,
			Priority:      claim.Priority,
			CLMFields:     claim.CLMFields,
			PatientName:   claim.PatientName,
			SubscriberID:  claim.SubscriberID,
			RefF8:         claim.RefF8,
			CompSep:       ":",
			Lines:         lineMap,
		})
	}
	return staging.WeaveSnapshot{
		Version: 1,
		Claims:  claims,
		Errors:  engine.Errors,
		Skipped: engine.Skipped,
	}
}

func (engine *Engine) logSkip(file, segRaw string) {
	engine.Skipped++
	engine.Errors = append(engine.Errors, file+": "+segRaw)
}

func (engine *Engine) ensureClaim(control string, priority int, fields []string) *claimState {
	claim, ok := engine.Claims[control]
	if !ok {
		claim = &claimState{
			ControlNumber: control,
			Priority:      priority,
			CLMFields:     fields,
			Lines:         make(map[int]*lineState),
		}
		engine.Claims[control] = claim
	}
	return claim
}

func (engine *Engine) ensureLine(claim *claimState, lx, priority int, inherited []string) *lineState {
	line, ok := claim.Lines[lx]
	if !ok {
		line = &lineState{
			LXSequence:        lx,
			Priority:          priority,
			InheritedPointers: append([]string(nil), inherited...),
		}
		claim.Lines[lx] = line
	}
	idx := CurrentClaimIndex(nil, claim.ControlNumber)
	AttachServiceLine(idx, lx, claim.Lines)
	return line
}

func appendClaimOrder(order []string, control string) []string {
	for _, existing := range order {
		if existing == control {
			return order
		}
	}
	return append(order, control)
}

func normalizeName(value string) string {
	return strings.Trim(value, " ")
}

func isPositiveInt(value string) bool {
	if value == "" {
		return false
	}
	for _, ch := range value {
		if ch < '0' || ch > '9' {
			return false
		}
	}
	return atoi(value) > 0
}

func atoi(value string) int {
	n := 0
	for _, ch := range value {
		n = n*10 + int(ch-'0')
	}
	return n
}

func parseHICodes(fields []string, compSep byte) []string {
	sep := string([]byte{compSep})
	codes := []string{}
	for _, element := range fields[1:] {
		if element == "" {
			continue
		}
		parts := strings.Split(element, sep)
		if len(parts) >= 2 && parts[1] != "" {
			codes = append(codes, parts[1])
		} else if len(parts) > 0 && parts[0] != "" {
			codes = append(codes, parts[0])
		}
	}
	return codes
}
