package ring

import (
	"encoding/json"
	"os"
	"path/filepath"

	"localauthz/internal/model"
)

func SaveRows(dir string, rows []model.GroupIndexRow) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	payload, err := json.MarshalIndent(rows, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "group_index.json"), append(payload, '\n'), 0o644)
}

func LoadRows(dir string) ([]model.GroupIndexRow, error) {
	path := filepath.Join(dir, "group_index.json")
	payload, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var rows []model.GroupIndexRow
	if err := json.Unmarshal(payload, &rows); err != nil {
		return nil, err
	}
	return rows, nil
}

func IndexFromRows(rows []model.GroupIndexRow) *MembershipIndex {
	idx := NewMembershipIndex()
	for _, row := range rows {
		if idx.groups[row.Group] == nil {
			idx.groups[row.Group] = map[string]model.GroupMember{}
		}
		for _, member := range row.Members {
			idx.groups[row.Group][member.Username] = member
		}
	}
	return idx
}
