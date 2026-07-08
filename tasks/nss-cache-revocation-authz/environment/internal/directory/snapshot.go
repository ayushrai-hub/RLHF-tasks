package directory

import (
	"sort"

	"localauthz/internal/model"
)

func NormalizeSnapshot(snap model.DirectorySnapshot) model.DirectorySnapshot {
	for i := range snap.Principals {
		sort.Strings(snap.Principals[i].Groups)
	}
	sort.SliceStable(snap.Principals, func(i, j int) bool {
		if snap.Principals[i].Username == snap.Principals[j].Username {
			return snap.Principals[i].SubjectID < snap.Principals[j].SubjectID
		}
		return snap.Principals[i].Username < snap.Principals[j].Username
	})
	return snap
}

func PrincipalByName(snap model.DirectorySnapshot, username string) (model.Principal, bool) {
	for _, p := range snap.Principals {
		if p.Username == username {
			return p, true
		}
	}
	return model.Principal{}, false
}
