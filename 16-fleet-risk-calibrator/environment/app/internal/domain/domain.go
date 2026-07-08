package domain

import "time"

type ServiceCall struct {
	RequestID       string
	AssetID         string
	AssetType       string
	Site            string
	OpenedAt        time.Time
	Priority        string
	TechnicianHours float64
	NotesCode       string
}

type SensorWindow struct {
	AssetID      string
	WindowEnd    time.Time
	TempC        *float64
	VibrationMMS float64
	PressureKPA  float64
	CurrentA     float64
	RuntimeHours float64
}

type Label struct {
	RequestID       string
	FailureWithin30 int
}

type HistoryEvent struct {
	AssetID   string
	EventTime time.Time
	EventType string
	Severity  int
}

type SiteCapacity struct {
	Site          string
	DispatchSlots int
	InspectSlots  int
}

type ScoredCall struct {
	Call           ServiceCall
	RawScore       float64
	CalibratedRisk float64
	DowntimeRisk   float64
	RiskBand       string
	Action         string
	TopFactor      string
	DueWithinHours int
	DecisionValue  float64
}

type ScheduledAction struct {
	RequestID   string
	CrewID      string
	Region      string
	Site        string
	Action      string
	StartAt     time.Time
	EndAt       time.Time
	TravelHours float64
}

type PartAllocation struct {
	RequestID     string
	PartID        string
	SourceSite    string
	DestSite      string
	Quantity      int
	ReadyAt       time.Time
	TransferHours float64
}
