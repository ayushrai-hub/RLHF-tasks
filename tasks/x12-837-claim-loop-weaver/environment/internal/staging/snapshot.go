package staging

import (
	"encoding/json"
	"os"
)

const SnapshotPath = "/app/state/weave-snapshot.json"

type LineSnapshot struct {
	LXSequence        int      `json:"lx_sequence"`
	Priority          int      `json:"priority"`
	SV1Fields         []string `json:"sv1_fields,omitempty"`
	HICodes           []string `json:"hi_codes,omitempty"`
	InheritedPointers []string `json:"inherited_pointers,omitempty"`
}

type ClaimSnapshot struct {
	ControlNumber string               `json:"control_number"`
	Priority      int                  `json:"priority"`
	CLMFields     []string             `json:"clm_fields"`
	PatientName   string               `json:"patient_name"`
	SubscriberID  string               `json:"subscriber_id"`
	RefF8         string               `json:"ref_f8"`
	CompSep       string               `json:"comp_sep"`
	Lines         map[int]LineSnapshot `json:"lines"`
}

type WeaveSnapshot struct {
	Version             int             `json:"version"`
	ManifestFingerprint string          `json:"manifest_fingerprint,omitempty"`
	Claims              []ClaimSnapshot `json:"claims"`
	Errors              []string        `json:"errors"`
	Skipped             int             `json:"skipped"`
}

func Write(path string, snap WeaveSnapshot) error {
	if snap.Version == 0 {
		snap.Version = 1
	}
	data, err := json.MarshalIndent(snap, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	if err := os.MkdirAll("/app/state", 0755); err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func Read(path string) (WeaveSnapshot, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return WeaveSnapshot{}, err
	}
	var snap WeaveSnapshot
	if err := json.Unmarshal(data, &snap); err != nil {
		return WeaveSnapshot{}, err
	}
	return snap, nil
}
