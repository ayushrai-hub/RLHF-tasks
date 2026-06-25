package main

// ApproverView is the cross-request rollup for a single approver.
type ApproverView struct {
	Approver        string   `json:"approver"`
	ApprovalsGiven  int      `json:"approvals_given"`  // lifetime approve decisions ever recorded
	ActiveApprovals int      `json:"active_approvals"` // current non-revoked approvals on live requests
	PendingRequests []string `json:"pending_requests"` // requests awaiting this approver at their current stage
}

// GroupView is the JSON projection of an approver group, with a rollup of the
// change requests that currently reference it.
type GroupView struct {
	ID                  string   `json:"id"`
	Name                string   `json:"name"`
	Members             []string `json:"members"`
	MemberCount         int      `json:"member_count"`
	ReferencingRequests []string `json:"referencing_requests"`
	Version             int      `json:"version"`
}

// StatsView is the service-wide rollup.
type StatsView struct {
	CRsCreated        int `json:"crs_created"`        // lifetime, survives delete
	CRsActive         int `json:"crs_active"`         // live, non-terminal
	ApprovalsRecorded int `json:"approvals_recorded"` // lifetime approve+reject records
	RevokesProcessed  int `json:"revokes_processed"`  // lifetime
	GroupsCreated     int `json:"groups_created"`     // lifetime, survives delete
}
