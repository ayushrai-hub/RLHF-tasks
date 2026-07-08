package ring

import (
	"sort"

	"localauthz/internal/model"
)

type MembershipIndex struct {
	groups map[string]map[string]model.GroupMember
}

func NewMembershipIndex() *MembershipIndex {
	return &MembershipIndex{groups: map[string]map[string]model.GroupMember{}}
}

func (m *MembershipIndex) ApplyPrincipal(p model.Principal) {
	if !p.Active {
		return
	}
	member := model.GroupMember{Username: p.Username, SubjectID: p.SubjectID, Generation: p.Generation}
	for _, group := range p.Groups {
		if m.groups[group] == nil {
			m.groups[group] = map[string]model.GroupMember{}
		}
		m.groups[group][p.Username] = member
	}
}

func (m *MembershipIndex) Contains(group string, username string) bool {
	members := m.groups[group]
	if members == nil {
		return false
	}
	_, ok := members[username]
	return ok
}

func (m *MembershipIndex) Rows() []model.GroupIndexRow {
	rows := make([]model.GroupIndexRow, 0, len(m.groups))
	for group, members := range m.groups {
		row := model.GroupIndexRow{Group: group, Members: make([]model.GroupMember, 0, len(members))}
		for _, member := range members {
			row.Members = append(row.Members, member)
		}
		sort.SliceStable(row.Members, func(i, j int) bool {
			if row.Members[i].Username == row.Members[j].Username {
				return row.Members[i].SubjectID < row.Members[j].SubjectID
			}
			return row.Members[i].Username < row.Members[j].Username
		})
		rows = append(rows, row)
	}
	sort.SliceStable(rows, func(i, j int) bool { return rows[i].Group < rows[j].Group })
	return rows
}
