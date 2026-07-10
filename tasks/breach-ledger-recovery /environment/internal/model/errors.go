package model

var errOrder = []string{
	"path_traversal",
	"archive_escape",
	"malformed_binary_frame",
	"identity_conflict",
	"host_conflict",
	"ssh_sequence_violation",
	"secret_fragment_conflict",
	"deleted_meta_conflict",
	"git_history_conflict",
	"process_conflict",
	"timeline_conflict",
	"missing_required_evidence",
}

func ME0(issues []Issue) *Issue {
	if len(issues) == 0 {
		return nil
	}
	for _, code := range errOrder {
		for i := range issues {
			if issues[i].Code == code {
				return &issues[i]
			}
		}
	}
	return &issues[0]
}

func AddIssue(issues *[]Issue, code string, message string) {
	*issues = append(*issues, Issue{Code: code, Message: message})
}
