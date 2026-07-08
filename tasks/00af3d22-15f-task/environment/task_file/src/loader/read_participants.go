package loader

import (
	"fmt"

	"tabsettle/model"
)

// ReadParticipants loads the ledger and returns the participant list.
func ReadParticipants(path string) ([]model.Participant, error) {
	var f model.ParticipantFile
	if err := readJSON(path, &f); err != nil {
		return nil, err
	}
	if len(f.Participants) == 0 {
		return nil, fmt.Errorf("no participants in %s", path)
	}
	return f.Participants, nil
}
