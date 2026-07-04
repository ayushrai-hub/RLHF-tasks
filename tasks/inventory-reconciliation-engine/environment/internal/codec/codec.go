package codec

import (
	"encoding/json"
	"strings"
	"time"

	"quotaledger/internal/domain"
)

type Event struct {
	EventID        string
	AccountID      string
	Operation      string
	Amount         *int
	LogicalTime    time.Time
	LogicalTimeStr string
	SourceReplica  string
	Seq            int
	Epoch          int
	TargetEventID  string
	ExpiresAt      string
	LineIndex      int
	Raw            map[string]any
}

type Rejection struct {
	EventID       string `json:"event_id"`
	AccountID     string `json:"account_id"`
	Reason        string `json:"reason"`
	PriorityRank  int    `json:"priority_rank"`
}

func NormalizeID(raw string) string {
	return strings.ToUpper(strings.TrimSpace(raw))
}

func ParseLogicalTime(raw string) (time.Time, error) {
	if !strings.HasSuffix(raw, "Z") {
		return time.Time{}, errBadTime
	}
	return time.Parse("2006-01-02T15:04:05", raw[:len(raw)-1])
}

var errBadTime = &parseError{"bad time"}

type parseError struct{ msg string }

func (e *parseError) Error() string { return e.msg }

func rejectionRow(eventID, accountID, reason string) *Rejection {
	return &Rejection{
		EventID:      eventID,
		AccountID:    accountID,
		Reason:       reason,
		PriorityRank: domain.RejectionRanks[reason],
	}
}

func ValidateEvent(obj map[string]any) (*Event, *Rejection) {
	required := []string{"event_id", "account_id", "operation", "logical_time", "source_replica", "seq", "epoch"}
	for _, field := range required {
		if obj[field] == nil {
			return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "missing_required")
		}
	}
	for key := range obj {
		if _, ok := domain.AllowedFields[key]; !ok {
			return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "unexpected_fields")
		}
	}

	if _, ok := obj["event_id"].(string); !ok {
		return nil, rejectionRow("", strVal(obj["account_id"]), "invalid_types")
	}
	if _, ok := obj["account_id"].(string); !ok {
		return nil, rejectionRow(strVal(obj["event_id"]), "", "invalid_types")
	}
	if _, ok := obj["source_replica"].(string); !ok {
		return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "invalid_types")
	}
	if _, ok := obj["operation"].(string); !ok {
		return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "invalid_types")
	}
	if _, ok := obj["logical_time"].(string); !ok {
		return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "invalid_types")
	}

	seq, seqOK := asInt(obj["seq"])
	if !seqOK {
		return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "invalid_types")
	}
	epoch, epochOK := asInt(obj["epoch"])
	if !epochOK {
		return nil, rejectionRow(strVal(obj["event_id"]), strVal(obj["account_id"]), "invalid_types")
	}

	eventID := NormalizeID(obj["event_id"].(string))
	accountID := NormalizeID(obj["account_id"].(string))
	replica := NormalizeID(obj["source_replica"].(string))
	op := strings.ToUpper(strings.TrimSpace(obj["operation"].(string)))

	if !domain.EventIDRe.MatchString(eventID) {
		return nil, rejectionRow(eventID, accountID, "invalid_event_id")
	}
	if !domain.AccountIDRe.MatchString(accountID) {
		return nil, rejectionRow(eventID, accountID, "invalid_account_id")
	}
	if !domain.ReplicaRe.MatchString(replica) {
		return nil, rejectionRow(eventID, accountID, "invalid_source_replica")
	}
	if _, ok := domain.MutatingOps[op]; !ok && op != "EXPIRE" {
		return nil, rejectionRow(eventID, accountID, "invalid_operation")
	}
	if op == "EXPIRE" {
		return nil, rejectionRow(eventID, accountID, "invalid_operation")
	}

	logicalTimeStr := obj["logical_time"].(string)
	logicalTime, err := ParseLogicalTime(logicalTimeStr)
	if err != nil {
		return nil, rejectionRow(eventID, accountID, "invalid_logical_time")
	}
	if seq < 1 {
		return nil, rejectionRow(eventID, accountID, "invalid_seq")
	}
	if epoch < 1 {
		return nil, rejectionRow(eventID, accountID, "invalid_epoch")
	}

	ev := &Event{
		EventID:        eventID,
		AccountID:      accountID,
		Operation:      op,
		LogicalTime:    logicalTime,
		LogicalTimeStr: logicalTimeStr,
		SourceReplica:  replica,
		Seq:            seq,
		Epoch:          epoch,
		Raw:            obj,
	}

	if _, needAmount := domain.AmountOps[op]; needAmount {
		amount, ok := asInt(obj["amount"])
		if !ok {
			return nil, rejectionRow(eventID, accountID, "invalid_amount")
		}
		if op == "CORRECTION" && amount < 0 {
			return nil, rejectionRow(eventID, accountID, "invalid_amount")
		}
		if op != "CORRECTION" && amount < 1 {
			return nil, rejectionRow(eventID, accountID, "invalid_amount")
		}
		ev.Amount = &amount
	} else if obj["amount"] != nil {
		return nil, rejectionRow(eventID, accountID, "invalid_amount")
	}

	if op == "REVERSAL" {
		target, ok := obj["target_event_id"]
		if target == nil {
			return nil, rejectionRow(eventID, accountID, "missing_target")
		}
		targetStr, ok := target.(string)
		if !ok {
			return nil, rejectionRow(eventID, accountID, "invalid_types")
		}
		targetID := NormalizeID(targetStr)
		if !domain.EventIDRe.MatchString(targetID) {
			return nil, rejectionRow(eventID, accountID, "invalid_target")
		}
		ev.TargetEventID = targetID
	} else if obj["target_event_id"] != nil {
		return nil, rejectionRow(eventID, accountID, "unexpected_fields")
	}

	if obj["expires_at"] != nil {
		if expStr, ok := obj["expires_at"].(string); ok {
			ev.ExpiresAt = expStr
		}
	}

	return ev, nil
}

func CanonicalPayload(obj map[string]any) map[string]any {
	out := make(map[string]any)
	keys := make([]string, 0, len(obj))
	for key := range obj {
		if _, ok := domain.AllowedFields[key]; ok {
			keys = append(keys, key)
		}
	}
	for _, key := range keys {
		val := obj[key]
		if val == nil {
			out[key] = nil
			continue
		}
		switch key {
		case "event_id", "account_id", "source_replica", "target_event_id":
			out[key] = NormalizeID(val.(string))
		case "operation":
			out[key] = strings.ToUpper(strings.TrimSpace(val.(string)))
		default:
			out[key] = val
		}
	}
	return out
}

func strVal(v any) string {
	if v == nil {
		return ""
	}
	if s, ok := v.(string); ok {
		return s
	}
	return ""
}

func asInt(v any) (int, bool) {
	switch n := v.(type) {
	case int:
		return n, true
	case float64:
		if n != float64(int(n)) {
			return 0, false
		}
		return int(n), true
	default:
		return 0, false
	}
}

func LoadJSONL(path string) ([][]byte, int, int, error) {
	data, err := readFile(path)
	if err != nil {
		return nil, 0, 0, err
	}
	lines := splitLines(data)
	var parsed [][]byte
	malformed := 0
	for _, line := range lines {
		if len(strings.TrimSpace(line)) == 0 {
			continue
		}
		var obj map[string]any
		if json.Unmarshal([]byte(line), &obj) != nil {
			malformed++
			continue
		}
		parsed = append(parsed, []byte(line))
	}
	return parsed, len(lines), malformed, nil
}
