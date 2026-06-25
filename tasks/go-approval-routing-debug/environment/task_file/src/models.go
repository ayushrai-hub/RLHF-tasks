package main

// Stage is one step in a change request's approval pipeline. A stage is
// satisfied once Required distinct eligible approvers have approved it. The
// effective eligible roster is the union of the literal Eligible ids and the
// current members of every group named in EligibleGroups, resolved live.
type Stage struct {
	Name           string   `json:"name"`
	Required       int      `json:"required"`
	Eligible       []string `json:"eligible"`
	EligibleGroups []string `json:"eligible_groups,omitempty"`
}

// Approval is a single recorded decision by an approver against a stage.
// Revoked decisions stay in history but no longer count toward quorum.
type Approval struct {
	Approver   string `json:"approver"`
	StageIndex int    `json:"stage_index"`
	Decision   string `json:"decision"` // "approve" or "reject"
	Seq        int    `json:"seq"`
	Revoked    bool   `json:"-"`
}

// ChangeRequest is a unit of work routed through an ordered approval pipeline.
type ChangeRequest struct {
	ID        string      `json:"id"`
	Title     string      `json:"title"`
	Author    string      `json:"author"`
	Stages    []Stage     `json:"stages"`
	Approvals []*Approval `json:"-"`
	Canceled  bool        `json:"-"`

	Revision int `json:"revision"`
	Version  int `json:"version"`
	Seq      int `json:"-"` // creation order, for stable sorting
}

// ChangeRequestUpdate is the body of PUT /change-requests/{id}. Pointer fields
// distinguish "omitted" (nil, leave as-is) from "set to zero value".
type ChangeRequestUpdate struct {
	Title  *string  `json:"title"`
	Stages *[]Stage `json:"stages"`
}

// CreateRequest is the body of POST /change-requests.
type CreateRequest struct {
	Title  string  `json:"title"`
	Author string  `json:"author"`
	Stages []Stage `json:"stages"`
}

// ApprovalRequest is the body of POST /change-requests/{id}/approvals.
type ApprovalRequest struct {
	Approver string `json:"approver"`
	Decision string `json:"decision"`
}

// ApproverGroup is a named, reusable roster of approvers referenced by stages.
type ApproverGroup struct {
	ID      string   `json:"id"`
	Name    string   `json:"name"`
	Members []string `json:"members"`
	Version int      `json:"version"`
	Seq     int      `json:"-"`
}

// GroupCreate is the body of POST /groups.
type GroupCreate struct {
	Name    string   `json:"name"`
	Members []string `json:"members"`
}

// GroupUpdate is the body of PUT /groups/{id}.
type GroupUpdate struct {
	Name    *string   `json:"name"`
	Members *[]string `json:"members"`
}

// Derived holds the computed routing state of a change request.
type Derived struct {
	Status        string `json:"status"`
	CurrentStage  int    `json:"current_stage"`
	RejectedBy    string `json:"rejected_by,omitempty"`
	RejectedStage int    `json:"rejected_stage,omitempty"`
}

// CRView is the JSON projection returned to clients.
type CRView struct {
	ID            string      `json:"id"`
	Title         string      `json:"title"`
	Author        string      `json:"author"`
	Stages        []Stage     `json:"stages"`
	Approvals     []*Approval `json:"approvals"`
	Status        string      `json:"status"`
	CurrentStage  int         `json:"current_stage"`
	RejectedBy    string      `json:"rejected_by,omitempty"`
	RejectedStage *int        `json:"rejected_stage,omitempty"`
	Revision      int         `json:"revision"`
	Version       int         `json:"version"`
}
