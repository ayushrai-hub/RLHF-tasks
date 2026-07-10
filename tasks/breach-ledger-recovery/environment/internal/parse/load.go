package parse

import (
	"path/filepath"

	"breach-ledger/internal/model"
)

func P0(root string) (model.Evidence, []model.Issue) {
	ev := model.Evidence{Summary: map[string]int{}}
	var issues []model.Issue
	unitA(filepath.Join(root, "inventory"), &ev, &issues)
	unitB(filepath.Join(root, "logs"), &ev, &issues)
	unitC(filepath.Join(root, "web"), &ev, &issues)
	unitD(filepath.Join(root, "histories"), &ev, &issues)
	unitE(filepath.Join(root, "persistence"), &ev, &issues)
	unitF(filepath.Join(root, "network"), &ev, &issues)
	unitG(filepath.Join(root, "audit"), &ev, &issues)
	unitH(filepath.Join(root, "deleted"), &ev, &issues)
	unitI(filepath.Join(root, "git"), &ev, &issues)
	unitJ(filepath.Join(root, "secrets"), &ev, &issues)
	unitK(filepath.Join(root, "archives"), &ev, &issues)
	unitL(filepath.Join(root, "configs"), &ev, &issues)
	unitM(filepath.Join(root, "proc"), &ev, &issues)
	unitN(filepath.Join(root, "containers"), &ev, &issues)
	return ev, issues
}
