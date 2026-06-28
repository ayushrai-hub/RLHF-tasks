package freezeengine

import "time"

type Config struct {
	ReviewThreshold            float64            `json:"review_threshold"`
	ApprovalRiskScore          float64            `json:"approval_risk_score"`
	ForcedReviewTypes          []string           `json:"forced_review_types"`
	TeamMap                    map[string]string  `json:"team_map"`
	ServiceClass               map[string]string  `json:"service_class"`
	ClassReviewThresholds      map[string]float64 `json:"class_review_thresholds"`
	PerServiceReviewThresholds map[string]float64 `json:"per_service_review_thresholds"`
	RegionFreezes              map[string]bool    `json:"region_freezes"`
}

type Request struct {
	ServiceID   string
	Timestamp   time.Time
	Seq         int
	Row         int
	RiskScore   float64
	ChangeType  string
	Region      string
	Blocked     bool
	Disabled    bool
	ForceReason string
}

type ServicePlan struct {
	ServiceID        string `json:"service_id"`
	Lane             string `json:"lane"`
	OwnerTeam        string `json:"owner_team"`
	RequiresApproval bool   `json:"requires_approval"`
	Reason           string `json:"reason"`
}
